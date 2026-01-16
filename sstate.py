#!/usr/bin/env python3
"""
sstate.py - U-M Cluster Partition & Node Summary Tool

Queries cluster node information using Slurm's scontrol and provides a compact,
colorful summary (CPU, memory, GPU) for each node and for totals.

Features:
- Works for all partitions, or can be limited to a specific partition using -p/--partition
- Handles nodes with/without GPUs
- Colorized output using the 'rich' library for fast resource assessment
- Usage help and guided error messages

Usage:
    ./sstate.py              # Show all nodes
    ./sstate.py -p gpu       # Show just the gpu partition
    ./sstate.py --partition standard

Requirements:
    pip install --user rich
"""

import argparse
import subprocess
import re
import sys

# Try to import rich, with user guidance if missing
try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("Error: This script requires the 'rich' Python package.\n"
          "Install it with: pip install --user rich\n")
    sys.exit(1)

def parse_args():
    """
    Parse command line arguments.
    Returns:
        argparse.Namespace: Parsed arguments object with .partition attribute.
    """
    parser = argparse.ArgumentParser(
        description="Query node data in Slurm and show resource summary.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="""
  sstate.py                # Show all nodes
  sstate.py -p PARTITION   # Show nodes in partition (e.g. sstate.py -p gpu)
        """.strip())
    parser.add_argument(
        "-p", "--partition",
        help="Query specific partition. If omitted, all nodes are shown.",
        type=str,
        metavar=""
    )
    return parser.parse_args()

def reformat_scontrol_output(scontrol_output):
    """
    Parse scontrol output into a list of per-node key=value strings for easier processing.
    Args:
        scontrol_output (str): Raw output from `scontrol show nodes --oneliner`
    Returns:
        list of lists: Each inner list is the node's attribute strings.
    """
    node_data_list = []
    for node_output in scontrol_output.strip().splitlines():
        # Split on key=, keep key in result for later parsing
        temp_data_list = []
        parts = re.split(r"([A-Z]\w+=)", node_output)
        for idx, part in enumerate(parts):
            if re.match(r"([A-Z]\w+=)", part):
                temp_data_list.append(part + parts[idx+1])
        node_data_list.append(temp_data_list)
    return node_data_list

def filter_partition_node_data(partition, node_data_list):
    """
    Select only nodes assigned to specified partition. If no partition, select all nodes.
    Args:
        partition (str or None): Partition name to filter, or None for all.
        node_data_list (list): List of node key=value lists.
    Returns:
        Filtered list of node key=value lists.
    """
    if not partition:
        return node_data_list  # No filtering needed
    partition_node_data_list = []
    for node in node_data_list:
        for line in node:
            if line.startswith("Partitions="):
                # Each node may serve multiple partitions (comma-separated)
                node_partitions = [p.strip().lower() for p in line.split("=")[1].split(",")]
                if partition.lower() in node_partitions:
                    partition_node_data_list.append(node)
                break  # Each node's partition data only needs checked once
    return partition_node_data_list

def parse_node_data(node_data_list):
    """
    For each node, parse out CPU/mem/GPU usage and print a color-coded table.
    Handles nodes with or without GPUs.
    Args:
        node_data_list (list): List of node key=value lists (as from reformat_scontrol_output).
    Returns: None
    """
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Node", style="bold")
    table.add_column("CPU (Alloc/Total)")
    table.add_column("MEM (GiB: Alloc/Total)")
    table.add_column("GPU (Alloc/Total)")
    table.add_column("State")

    # Accumulators for cluster totals
    totals = {
        'nodes': 0, 'cpu_alloc':0, 'cpu_tot':0,
        'mem_alloc':0, 'mem_tot':0,
        'gpu_alloc':0, 'gpu_tot':0,
    }
    gpu_present = False

    for node in node_data_list:
        # Set defaults in case certain keys are missing
        node_name = "?"
        cpu_alloc = cpu_tot = 0
        mem_alloc = mem_tot = 0
        gpu_alloc = gpu_tot = None
        node_state = "?"

        # Parse node attributes into variables
        for line in node:
            try:
                key = re.split(r"([A-Z]\w+)(?==)", line)[1]
                value = re.split(r"([A-Z]\w+=)", line)[2]
            except Exception:
                continue  # Skip any unparseable attribute

            # Assign fields based on key
            if key == "NodeName":
                node_name = value
            elif key == "CPUAlloc":
                try: cpu_alloc = int(value)
                except ValueError: cpu_alloc = 0
            elif key == "CPUTot":
                try: cpu_tot = int(value)
                except ValueError: cpu_tot = 0
            elif key == "AllocMem":
                try: mem_alloc = int(value) / 1024  # MB -> GiB
                except ValueError: mem_alloc = 0
            elif key == "RealMemory":
                try: mem_tot = int(value) / 1024
                except ValueError: mem_tot = 0
            elif key == "State":
                node_state = value
            elif key == "CfgTRES":
                if "gres/gpu" in value:
                    try:
                        # Format: ...gres/gpu=X
                        gpu_tot = int(value.split(",")[-1].split("=")[1])
                    except Exception:
                        gpu_tot = None
            elif key == "AllocTRES":
                if "gres/gpu" in value:
                    try:
                        gpu_alloc = int(value.split(",")[-1].split("=")[1])
                    except Exception:
                        gpu_alloc = None

        # Compute used percentages where possible for coloring
        cpu_pct = int(round(cpu_alloc / cpu_tot * 100)) if cpu_tot else None
        mem_pct = int(round(mem_alloc / mem_tot * 100)) if mem_tot else None
        if isinstance(gpu_alloc, int) and isinstance(gpu_tot, int) and gpu_tot > 0:
            gpu_pct = int(round(gpu_alloc / gpu_tot * 100))
            gpu_present = True
        else:
            gpu_pct = None

        def color(val, pct):
            """
            Colorizes value according to percentage used.
            Returns a string with rich markup.
            """
            if pct is None: return str(val)
            if pct < 50: return f"[green]{val}[/]"
            elif pct < 80: return f"[yellow]{val}[/]"
            else: return f"[red]{val}[/]"

        cpu_str = f"{color(cpu_alloc, cpu_pct)}/{cpu_tot}"
        mem_str = f"{color(int(mem_alloc), mem_pct)}/{int(mem_tot)}"
        if gpu_present and gpu_pct is not None and gpu_tot is not None:
            gpu_str = f"{color(gpu_alloc, gpu_pct)}/{gpu_tot}"
        else:
            gpu_str = "--/--"

        table.add_row(node_name, cpu_str, mem_str, gpu_str, node_state)

        # Accumulate totals for summary row
        totals['nodes'] += 1
        totals['cpu_alloc'] += cpu_alloc
        totals['cpu_tot'] += cpu_tot
        totals['mem_alloc'] += mem_alloc
        totals['mem_tot'] += mem_tot
        if gpu_present and isinstance(gpu_alloc, int) and isinstance(gpu_tot, int):
            totals['gpu_alloc'] += gpu_alloc
            totals['gpu_tot'] += gpu_tot

    # Add totals summary row if any nodes were processed
    if totals['cpu_tot'] > 0 and totals['mem_tot'] > 0 and totals['nodes'] > 0:
        total_cpu_pct = int(round(totals['cpu_alloc']/totals['cpu_tot']*100))
        total_mem_pct = int(round(totals['mem_alloc']/totals['mem_tot']*100))
        cpu_str = f"{color(totals['cpu_alloc'], total_cpu_pct)}/{totals['cpu_tot']}"
        mem_str = f"{color(int(totals['mem_alloc']), total_mem_pct)}/{int(totals['mem_tot'])}"

        if gpu_present and totals['gpu_tot']:
            total_gpu_pct = int(round(totals['gpu_alloc']/totals['gpu_tot']*100))
            gpu_str = f"{color(totals['gpu_alloc'], total_gpu_pct)}/{totals['gpu_tot']}"
        else:
            gpu_str = "--/--"

        table.add_row("[b]Totals[/b]", cpu_str, mem_str, gpu_str, "")

    if totals['nodes'] == 0:
        console.print("[red]No nodes found in this partition. Check your partition name or Slurm state.[/]")
    else:
        console.print(table)

def main():
    """
    Main execution flow: parses arguments, calls scontrol, parses node data, and prints result.
    """
    args = parse_args()

    # Run scontrol and collect node data
    try:
        scontrol_output = subprocess.check_output(
            "/usr/bin/scontrol show nodes --oneliner", shell=True, text=True
        )
    except FileNotFoundError:
        print("[red]Error: scontrol not found. Are you running on a Slurm management node?[/]")
        sys.exit(2)
    except subprocess.CalledProcessError as e:
        print(f"[red]Failed to query nodes with scontrol: {e}[/]")
        sys.exit(2)

    node_data_list = reformat_scontrol_output(scontrol_output)
    filtered_node_data_list = filter_partition_node_data(args.partition, node_data_list)

    if not filtered_node_data_list:
        print("[red]No nodes matched the given partition (or no nodes found at all).[/]")
        suggestions = "- Check your partition name with 'sinfo'\n" \
                      "- Run without -p/--partition for all nodes"
        print(suggestions)
        sys.exit(0)

    parse_node_data(filtered_node_data_list)

if __name__ == "__main__":
    main()
