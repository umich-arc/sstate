#!/bin/env python3

from tabulate import tabulate
import subprocess
import argparse


# This function converts MB to larger units
def human_readable(num, suffix='B'):
    for unit in ['Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--partition", help="Specify partition (standard, gpu, largemem, debug, standard-oc). "
                                                  "If this is not specified all nodes will be shown")
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()
    # Calls the scontrol script and gets its output
    output = subprocess.check_output('/opt/slurm/bin/scontrol show nodes --oneliner', shell=True).decode()

    # Initializes variables to track values
    rows = []
    overall_node = 0
    overall_alloc_cpu = 0
    overall_available_cpu = 0
    overall_total_cpu = 0
    overall_cpu_load = 0

    overall_alloc_mem = 0
    overall_available_mem = 0
    overall_total_mem = 0

    overall_alloc_gpu = 0
    overall_available_gpu = 0
    overall_total_gpu = 0

    # Every line represents a new node
    for line in output.splitlines():
        # If a partition is specified, only those values are shown
        if args.partition and args.partition != 'all':
            # Initializes a bool that will send the loop back to the start if the partition is incorrect
            back_to_start = False
            # Searches for the partition tag
            for pair in line.split():
                if pair.split('=')[0] == 'Partitions':
                    # If the partition is debug, only shows the nodes that exclusively specified debug
                    if args.partition == 'debug':
                        if pair.split('=')[1] != 'debug':
                            back_to_start = True
                            break
                    else:
                        # Searches if the correct partition is listed in the partition tags for that node
                        found_correct_partition = False
                        for parition_type in pair.split('=')[1].split(','):
                            if parition_type == args.partition:
                                found_correct_partition = True
                                break
                        # If the correct partition is not found, the line is ignored and a new line is loaded
                        if not found_correct_partition:
                            back_to_start = True
                            break
            if back_to_start:
                continue


        overall_node += 1

        # This gets all key value pairs by splitting the line on whitespace
        key_vals = line.split()
        node_name = key_vals[0].split("=")[1]

        # Initializes the GPU variables to N/A. This gets overwritten if the node has GPUs
        gpu_tot = 'N/A'
        gpu_alloc = 'N/A'
        percent_used_gpu = 'N/A'

        # Loops through all key value pairs in the line
        for pair in key_vals:
            # Gets the key of the pair
            key = pair.split('=')[0]

            # Only gets the value if there is one
            val = None
            if len(pair.split('=')) > 1:
                val = pair.split('=')[1]

            # Changes values based on key
            if key == 'CPUAlloc':
                try:
                    cpu_alloc = int(val)
                    overall_alloc_cpu += cpu_alloc
                except ValueError:
                    cpu_alloc = 0
                    overall_alloc_cpu += cpu_alloc
            elif key == 'CPUTot':
                try:
                    cpu_tot = int(val)
                    overall_total_cpu += cpu_tot
                except ValueError:
                    cpu_tot = 0
                    overall_total_cpu += cpu_tot
            elif key == 'CPULoad':
                try:
                    cpu_load = float(val)
                    overall_cpu_load += cpu_load
                except ValueError:
                    cpu_load = float(0)
                    overall_cpu_load += cpu_load
            elif key == 'RealMemory':
                try:
                    total_mem = int(val)
                    overall_total_mem += total_mem
                except ValueError:
                    total_mem = 0
                    overall_total_mem += total_mem
            elif key == 'AllocMem':
                try:
                    alloc_mem = int(val)
                    overall_alloc_mem += alloc_mem
                except ValueError:
                    alloc_mem = 0
                    overall_alloc_mem += alloc_mem
            elif key == 'State':
                node_state = val
            elif key == 'CfgTRES':
                # If there is gpu data, gets the total number of gpus
                if 'gres/gpu' in pair:
                    try:
                        gpu_tot = int(pair.split(",")[-1].split("=")[1])
                        overall_total_gpu += gpu_tot
                    except ValueError:
                        gpu_tot = 0
                        overall_total_gpu += gpu_tot
            elif key == 'AllocTRES':
                # If there is gpu data, get the allocated number of gpus
                if 'gres/gpu' in pair:
                    try:
                        gpu_alloc = int(pair.split(",")[-1].split("=")[1])
                        overall_alloc_gpu += gpu_alloc
                    except ValueError:
                        gpu_alloc = 0
                        overall_alloc_gpu += gpu_alloc

        # Calculates percent used for cpu
        percent_used_cpu = 0
        if cpu_tot > 0:
            percent_used_cpu = cpu_alloc / cpu_tot * 100

        # Calculates available cpus
        cpu_avail = cpu_tot
        if cpu_alloc != 0:
            cpu_avail = cpu_tot - cpu_alloc

        # Calculates percent used for memory
        percent_used_mem = 0
        if total_mem > 0:
            percent_used_mem = alloc_mem / total_mem * 100

        # Calculates available memory
        avail_mem = total_mem
        if alloc_mem != 0:
            avail_mem = total_mem - alloc_mem

        # If there are GPUs but none are allocated, sets GPU allocated to 0
        if type(gpu_alloc) is str and type(gpu_tot) is int:
            gpu_alloc = 0
        # Calculates percent used for GPU
        if type(gpu_alloc) is int and type(gpu_tot) is int:
            percent_used_gpu = gpu_alloc / gpu_tot * 100

        # Calculates available gpus
        gpu_avail = gpu_tot
        if gpu_alloc != "N/A" and gpu_alloc != 0:
            gpu_avail = gpu_tot - gpu_alloc

        # Adjust available resources based on full allocated resources
        if cpu_alloc == cpu_tot:
            avail_mem = 0
            if gpu_alloc != "N/A":
                gpu_avail = 0
        if alloc_mem == total_mem:
            cpu_avail = 0
            if gpu_alloc != "N/A":
                gpu_avail = 0
        if gpu_alloc != "N/A":
            if gpu_alloc == gpu_tot:
                cpu_avail = 0
                avail_mem = 0

        # Calculate the available resources
        overall_available_cpu += cpu_avail
        overall_available_mem += avail_mem
        if gpu_avail != "N/A":
            overall_available_gpu += gpu_avail

        # Swaps the allocated memory, total memory, and available memory to a human readable format for the table
        alloc_mem = human_readable(alloc_mem)
        total_mem = human_readable(total_mem)
        avail_mem = human_readable(avail_mem)

        rows.append([node_name, cpu_alloc, cpu_avail, cpu_tot, percent_used_cpu, cpu_load, alloc_mem, avail_mem, total_mem, percent_used_mem,
                     gpu_alloc, gpu_avail, gpu_tot, percent_used_gpu, node_state])

    # Calculates the overall percent used for cpu
    overall_percent_used_cpu = 0
    if overall_total_cpu > 0:
        overall_percent_used_cpu = overall_alloc_cpu / overall_total_cpu * 100

    # Calculates the average cpu load
    if overall_node > 0:
        overall_cpu_load = overall_cpu_load / overall_node

    # Calculates the overall percent used for mem
    overall_percent_used_mem = 0
    if overall_total_mem > 0:
        overall_percent_used_mem = overall_alloc_mem / overall_total_mem * 100

    # Swaps the overall allocated memory, total memory, and available memory to a human readable format for the table
    overall_alloc_mem = human_readable(overall_alloc_mem)
    overall_total_mem = human_readable(overall_total_mem)
    overall_available_mem = human_readable(overall_available_mem)

    # Calculates the overall percent used for gpu
    overall_percent_used_gpu = 'N/A'
    if overall_total_gpu > 0:
        overall_percent_used_gpu = overall_alloc_gpu / overall_total_gpu * 100

    # Prints a table with the node statistics
    print(tabulate(rows, headers=['Node', 'AllocCPU', 'AvailCPU', 'TotalCPU', 'PercentUsedCPU', 'CPULoad', 'AllocMem', 'AvailMem', 'TotalMem',
                                  'PercentUsedMem', 'AllocGPU', 'AvailGPU', 'TotalGPU', 'PercentUsedGPU', 'NodeState'], floatfmt=".2f"))

    print("\nTotals:")

    # Prints the overall statistics
    print(tabulate([[overall_node, overall_alloc_cpu, overall_available_cpu, overall_total_cpu, overall_percent_used_cpu, overall_cpu_load,
                    overall_alloc_mem, overall_available_mem, overall_total_mem, overall_percent_used_mem, overall_alloc_gpu,
                    overall_available_gpu, overall_total_gpu, overall_percent_used_gpu]],
                   headers=['Node', 'AllocCPU', 'AvailCPU', 'TotalCPU', 'PercentUsedCPU', 'CPULoad', 'AllocMem', 'AvailMem', 'TotalMem',
                            'PercentUsedMem', 'AllocGPU', 'AvailGPU', 'TotalGPU', 'PercentUsedGPU'], floatfmt=".2f"))
