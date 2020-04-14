from tabulate import tabulate
import subprocess

def human_readable(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


if __name__ == '__main__':
    output = subprocess.check_output('/opt/slurm/bin/scontrol show nodes --oneliner | head -2', shell=True).decode()

    rows = []
    for line in output.splitlines():
        key_vals = line.split()
        node_name = key_vals[0].split("=")[1]
        gpu_tot = 'N/A'
        gpu_alloc = 'N/A'
        for pair in key_vals:
            key = pair.split('=')[0]
            val = None
            if len(pair.split('=')) > 1:
                val = pair.split('=')[1]

            if key == 'CPUAlloc':
                cpu_alloc = int(val)
            elif key == 'CPUTot':
                cpu_tot = int(val)
            elif key == 'CPULoad':
                cpu_load = val
            elif key == 'RealMemory':
                total_mem = int(val)
            elif key == 'AllocMem':
                alloc_mem = int(val)
            elif key == 'State':
                node_state = val
            elif key == 'CfgTRES':
                if 'gres/gpu' in pair:
                    gpu_tot = int(pair.split(",")[-1].split("=")[1])
            elif key == 'AllocTRES':
                if 'gres/gpu' in pair:
                    gpu_alloc = int(pair.split(",")[-1].split("=")[1])

        percent_used_cpu = cpu_alloc / cpu_tot
        percent_used_mem = alloc_mem / total_mem
        percent_used_gpu = gpu_alloc / gpu_tot

        alloc_mem = human_readable(alloc_mem)
        total_mem = human_readable(total_mem)

        rows.append([node_name, cpu_alloc, cpu_tot, percent_used_cpu, cpu_load, alloc_mem, total_mem, percent_used_mem,
                     gpu_alloc, gpu_tot, percent_used_gpu, node_state])

    print(tabulate(rows, headers=['Node', 'AllocCPU', 'TotalCPU', 'PercentUsedCPU', 'CPULoad', 'AllocMem', 'TotalMem',
                                  'PercentUsedMem', 'AllocGPU', 'TotalGPU', 'PercentUsedGPU', 'NodeState']))
