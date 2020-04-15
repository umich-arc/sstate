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
    parser.add_argument("-p", "--partition", help="Specify partition (standard, gpu, largemem, debug, standard-oc)")
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
    overall_total_cpu = 0
    overall_cpu_load = 0

    overall_alloc_mem = 0
    overall_total_mem = 0

    overall_alloc_gpu = 0
    overall_total_gpu = 0

    # Every line represents a new node
    for line in output.splitlines():
        if args.partition:
            for pair in line.split():
                if pair.split('=')[0] == 'Partitions':
                    print("True")
                    if args.partition == 'debug':
                        if pair.split('=')[1] != 'debug':
                            continue
                    else:
                        found_correct_partition = False
                        for parition_type in pair.split('=')[1].split(','):
                            if parition_type == args.partition:
                                found_correct_partition = True
                                break
                        if not found_correct_partition:
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
                cpu_alloc = int(val)
                overall_alloc_cpu += cpu_alloc
            elif key == 'CPUTot':
                cpu_tot = int(val)
                overall_total_cpu += cpu_tot
            elif key == 'CPULoad':
                cpu_load = float(val)
                overall_cpu_load += cpu_load
            elif key == 'RealMemory':
                total_mem = int(val)
                overall_total_mem += total_mem
            elif key == 'AllocMem':
                alloc_mem = int(val)
                overall_alloc_mem += alloc_mem
            elif key == 'State':
                node_state = val
            elif key == 'CfgTRES':
                # If there is gpu data, gets the total number of gpus
                if 'gres/gpu' in pair:
                    gpu_tot = int(pair.split(",")[-1].split("=")[1])
                    overall_total_gpu += gpu_tot
            elif key == 'AllocTRES':
                # If there is gpu data, get the allocated number of gpus
                if 'gres/gpu' in pair:
                    gpu_alloc = int(pair.split(",")[-1].split("=")[1])
                    overall_alloc_gpu += gpu_alloc

        percent_used_cpu = cpu_alloc / cpu_tot
        percent_used_mem = alloc_mem / total_mem
        if type(gpu_alloc) is str and type(gpu_tot) is int:
            gpu_alloc = 0
        if type(gpu_alloc) is int and type(gpu_tot) is int:
            percent_used_gpu = gpu_alloc / gpu_tot

        alloc_mem = human_readable(alloc_mem)
        total_mem = human_readable(total_mem)

        rows.append([node_name, cpu_alloc, cpu_tot, percent_used_cpu, cpu_load, alloc_mem, total_mem, percent_used_mem,
                     gpu_alloc, gpu_tot, percent_used_gpu, node_state])

    overall_percent_used_cpu = overall_alloc_cpu / overall_total_cpu
    overall_cpu_load = overall_cpu_load / overall_node

    overall_percent_used_mem = overall_alloc_mem / overall_total_mem

    overall_alloc_mem = human_readable(overall_alloc_mem)
    overall_total_mem = human_readable(overall_total_mem)

    overall_percent_used_gpu = overall_alloc_gpu / overall_total_gpu

    print(tabulate(rows, headers=['Node', 'AllocCPU', 'TotalCPU', 'PercentUsedCPU', 'CPULoad', 'AllocMem', 'TotalMem',
                                  'PercentUsedMem', 'AllocGPU', 'TotalGPU', 'PercentUsedGPU', 'NodeState']))

    print("\nTotals:")

    print(tabulate([[overall_node, overall_alloc_cpu, overall_total_cpu, overall_percent_used_cpu, overall_cpu_load,
                    overall_alloc_mem, overall_total_mem, overall_percent_used_mem, overall_alloc_gpu,
                     overall_total_gpu, overall_percent_used_gpu]],
                   headers=['Node', 'AllocCPU', 'TotalCPU', 'PercentUsedCPU', 'CPULoad', 'AllocMem', 'TotalMem',
                            'PercentUsedMem', 'AllocGPU', 'TotalGPU', 'PercentUsedGPU']))
