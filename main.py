import psutil
import time
import os
import subprocess
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.console import Console

console = Console()

# Температура — автоопределение
def get_temp():
    try:
        output = subprocess.check_output("sensors", encoding='utf-8')
        for line in output.splitlines():
            if any(k in line for k in ["Package id", "Tctl", "edge", "Composite"]):
                temp = line.split()[1]
                return temp.replace('+', '')
    except Exception as e:
        console.log(f"Error getting temperature: {e}")
        return "N/A"


# Аптайм
def get_uptime():
    uptime_sec = time.time() - psutil.boot_time()
    mins, secs = divmod(int(uptime_sec), 60)
    hours, mins = divmod(mins, 60)
    return f"{hours}h {mins}m"


# Получаем имена пользователей без повторений
def get_users():
    users = psutil.users()
    user_info = set()  # Используем set для уникальности пользователей
    for user in users:
        user_info.add(user.name)  # Добавляем имя пользователя в set
    if not user_info:
        user_info = "No users logged in."
    else:
        user_info = "\n".join(user_info)  # Преобразуем set обратно в строку
    return user_info


# Модель процессора
def get_cpu_model():
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpu_info = f.read()
        for line in cpu_info.splitlines():
            if line.startswith("model name"):
                return line.split(":")[1].strip()
        return "N/A"
    except Exception as e:
        return f"Error: {e}"


# Модель видеокарты (определяет автоматически, если это NVIDIA или AMD)
def get_gpu_model():
    try:
        # Проверка на NVIDIA
        nvidia_check = subprocess.check_output("nvidia-smi", shell=True, stderr=subprocess.PIPE, encoding='utf-8')
        if "NVIDIA" in nvidia_check:
            # Если это NVIDIA, получаем модель через nvidia-smi
            output = subprocess.check_output("nvidia-smi --query-gpu=gpu_name --format=csv,noheader", shell=True, encoding='utf-8')
            return output.strip()
    except subprocess.CalledProcessError:
        pass  # Если nvidia-smi не найдено, пробуем для AMD

    try:
        # Проверка на AMD
        output = subprocess.check_output("lspci | grep VGA", shell=True, encoding='utf-8')
        # Извлекаем название модели карты
        if "AMD" in output or "ATI" in output:
            # Просто извлекаем нужную часть строки
            gpu_name = output.split(":")[2].strip()
            # Оставляем только основное название карты
            return " ".join(gpu_name.split()[:4])  # Только первые четыре слова
        else:
            return "Unknown GPU"
    except subprocess.CalledProcessError:
        return "N/A"
    except Exception as e:
        return f"Error: {e}"


# Основной HUD
def make_hud():
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage('/')
    net = psutil.net_io_counters()
    load1, load5, load15 = os.getloadavg()
    temp = get_temp()
    battery = psutil.sensors_battery()

    # Количество процессов
    processes = len(psutil.pids())

    # Статистика CPU
    user_cpu, system_cpu, idle_cpu = psutil.cpu_times_percent(interval=None)[:3]
    user_cpu_str = f"[bold green]{user_cpu}%[/bold green]" if user_cpu < 80 else f"[bold orange1]{user_cpu}%[/bold orange1]"
    system_cpu_str = f"[bold green]{system_cpu}%[/bold green]" if system_cpu < 80 else f"[bold orange1]{system_cpu}%[/bold orange1]"
    idle_cpu_str = f"[bold green]{idle_cpu}%[/bold green]" if idle_cpu > 20 else f"[bold red]{idle_cpu}%[/bold red]"

    # CPU
    cpu_str = f"{cpu}%"
    if cpu > 90:
        cpu_str = f"[bold red]{cpu}%[/bold red]  [bold red]!!! CRITICAL !!![/bold red]"
    elif cpu > 80:
        cpu_str = f"[bold orange1]{cpu}%[/bold orange1]  [bold orange1]!!! HIGH !!![/bold orange1]"
    else:
        cpu_str = f"[bold green]{cpu}%[/bold green]"

    # RAM
    if ram.percent > 90:
        ram_str = f"[bold yellow]{ram.percent}%[/bold yellow]  [bold red]!!! CRITICAL !!![/bold red]"
    elif ram.percent > 80:
        ram_str = f"[bold yellow]{ram.percent}%[/bold yellow]  [bold orange1]!!! HIGH !!![/bold orange1]"
    else:
        ram_str = f"[bold green]{ram.percent}%[/bold green]"

    # Temp
    if temp != "N/A":
        try:
            temp_val = float(temp[:-2])  # отбрасываем °C
            if temp_val > 85:
                temp_str = f"[bold magenta]{temp}[/bold magenta]  [bold red]!!! CRITICAL !!![/bold red]"
            elif temp_val > 75:
                temp_str = f"[bold magenta]{temp}[/bold magenta]  [bold orange1]!!! HIGH !!![/bold orange1]"
            else:
                temp_str = f"[bold magenta]{temp}[/bold magenta]"
        except:
            temp_str = f"[bold magenta]{temp}[/bold magenta]"
    else:
        temp_str = "[dim]N/A[/dim]"

    # Disk
    if disk.percent > 90:
        disk_str = f"[bold red]{disk.percent}%[/bold red]  [bold red]!!! CRITICAL !!![/bold red]"
    elif disk.percent > 80:
        disk_str = f"[bold orange1]{disk.percent}%[/bold orange1]  [bold orange1]!!! HIGH !!![/bold orange1]"
    else:
        disk_str = f"[bold green]{disk.percent}%[/bold green]"

    # Load
    load_str = f"{load1:.2f}"
    if load1 > psutil.cpu_count():
        load_str = f"[bold red]{load_str}[/bold red]  [bold red]!!! OVERLOADED !!![/bold red]"
    elif load1 > psutil.cpu_count() * 0.75:
        load_str = f"[bold orange1]{load_str}[/bold orange1]  [bold orange1]!!! HIGH !!![/bold orange1]"
    else:
        load_str = f"[bold green]{load_str}[/bold green]"

    # Swap
    swap_str = f"{swap.percent}%"
    if swap.percent > 50:
        swap_str = f"[bold red]{swap.percent}%[/bold red]  [bold red]!!! CRITICAL !!![/bold red]"
    elif swap.percent > 30:
        swap_str = f"[bold orange1]{swap.percent}%[/bold orange1]  [bold orange1]!!! HIGH !!![/bold orange1]"
    else:
        swap_str = f"[bold green]{swap.percent}%[/bold green]"

    # Battery
    battery_str = "N/A"
    if battery:
        battery_str = f"{battery.percent:.2f}%"  # Форматируем до 2 знаков после запятой
        if battery.power_plugged:
            battery_str = f"[bold green]{battery_str}[/bold green] (charging)"
        elif battery.percent < 20:
            battery_str = f"[bold red]{battery_str}[/bold red]  [bold red]!!! LOW !!![/bold red]"
        else:
            battery_str = f"[bold green]{battery_str}[/bold green]"

    # Модели процессора и видеокарты
    cpu_model = get_cpu_model()
    gpu_model = get_gpu_model()

    # Таблица HUD
    table = Table.grid(padding=1)
    table.add_column(justify="right")
    table.add_column(justify="left")

    table.add_row("🧠 CPU Load:", cpu_str)
    table.add_row("💾 RAM Used:", ram_str)
    table.add_row("🔁 Swap Used:", swap_str)
    table.add_row("🌡️ Temp:", temp_str)
    table.add_row("📀 Disk Usage:", disk_str)
    table.add_row("⚙️ Load Avg:", load_str)
    table.add_row("👥 Processes:", f"[bold cyan]{processes}[/bold cyan]")
    table.add_row("🧑‍💻 Users:", get_users())
    table.add_row("📡 Net Sent:", f"{net.bytes_sent // 1024} KB")
    table.add_row("📥 Net Recv:", f"{net.bytes_recv // 1024} KB")
    table.add_row("🔋 Battery:", battery_str)
    table.add_row("⏱️ Uptime:", f"{get_uptime()}")
    table.add_row("🖥️ CPU Model:", cpu_model)
    table.add_row("🎮 GPU Model:", gpu_model)

    panel = Panel(table, title="[bold green]SYSTEM HUD v1.0[/bold green]", border_style="bright_blue")
    return panel


# Главный цикл
def main():
    with Live(make_hud(), refresh_per_second=1) as live:
        while True:
            time.sleep(1)
            live.update(make_hud())


main()
