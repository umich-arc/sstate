from tabulate import tabulate
import subprocess

def human_readable(num, suffix='B'):
    for unit in ['Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


if __name__ == '__main__':
    output = subprocess.check_output('/opt/slurm/bin/scontrol show nodes --oneliner', shell=True).decode()

    rows = []
    overall_node = 0
    overall_alloc_cpu = 0
    overall_total_cpu = 0
    overall_cpu_load = 0

    overall_alloc_mem = 0
    overall_total_mem = 0

    overall_alloc_gpu = 0
    overall_total_gpu = 0
    for line in output.splitlines():
        overall_node += 1
        key_vals = line.split()
        node_name = key_vals[0].split("=")[1]
        gpu_tot = 'N/A'
        gpu_alloc = 'N/A'
        percent_used_gpu = 'N/A'
        for pair in key_vals:
            key = pair.split('=')[0]
            val = None
            if len(pair.split('=')) > 1:
                val = pair.split('=')[1]

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
                if 'gres/gpu' in pair:
                    gpu_tot = int(pair.split(",")[-1].split("=")[1])
                    overall_total_gpu += gpu_tot
            elif key == 'AllocTRES':
                if 'gres/gpu' in pair:
                    gpu_alloc = int(pair.split(",")[-1].split("=")[1])
                    overall_alloc_gpu += gpu_alloc

        percent_used_cpu = cpu_alloc / cpu_tot
        percent_used_mem = alloc_mem / total_mem
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

    print("Totoals:")

    print(tabulate([[overall_node, overall_alloc_cpu, overall_total_cpu, overall_percent_used_cpu, overall_cpu_load,
                    overall_alloc_mem, overall_total_mem, overall_percent_used_mem, overall_alloc_gpu,
                     overall_total_gpu, overall_percent_used_gpu]],
                   headers=['Node', 'AllocCPU', 'TotalCPU', 'PercentUsedCPU', 'CPULoad', 'AllocMem', 'TotalMem',
                            'PercentUsedMem', 'AllocGPU', 'TotalGPU', 'PercentUsedGPU']))
    