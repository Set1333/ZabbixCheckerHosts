import aiohttp
import asyncio
import csv
import logging

# Zabbix servers configuration
zabbix_servers = [
    {"name": "slave", "url": "https://slave.zabbix.com/api_jsonrpc.php", "user": "USER", "password": "PASS"},
    {"name": "master", "url": "https://master.zabbix.com/api_jsonrpc.php", "user": "USER", "password": "PASS"},
    {"name": "reserved", "url": "https://res.zabbix.com/api_jsonrpc.php", "user": "user": "USER", "password": "PASS"},
]

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def get_zabbix_token(session, zabbix_server):
    url = zabbix_server["url"]
    user = zabbix_server["user"]
    password = zabbix_server["password"]
    headers = {"Content-Type": "application/json-rpc"}
    data = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "user": user,
            "password": password
        },
        "id": 1,
        "auth": None
    }

    async with session.post(url, headers=headers, json=data, ssl=False) as response:
        result = await response.json()
        if "result" in result:
            logging.info(f"Авторизация успешна {url}")
            return result["result"]
        else:
            logging.error(f"Авторизация не удалась {url}: {result}")
            return None


async def host_exists(session, zabbix_server, hostname, token):
    url = zabbix_server["url"]
    headers = {"Content-Type": "application/json-rpc"}
    data = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "search": {
                "host": [hostname]
            },
            "searchByAny": True
        },
        "auth": token,
        "id": 1,
    }

    async with session.post(url, headers=headers, json=data, ssl=False) as response:
        result = await response.json()
        exists = len(result["result"]) > 0
        logging.info(f"Проверка хоста '{hostname}' на сервере '{url}': {'Хост найден' if exists else 'Хост не найден'}")
        return exists


async def check_host_on_all_servers(session, hostnames, zabbix_server):
    token = await get_zabbix_token(session, zabbix_server)
    results = []

    if token:
        for hostname in hostnames:
            exists = await host_exists(session, zabbix_server, hostname, token)
            if exists:
                results.append({"hostname": hostname, "zabbix_server": zabbix_server["name"]})
        print(f"Сервер '{zabbix_server['url']}' проверено: {len(results)} хост найден.")
    return results


async def check_hosts_in_zabbix_servers(hostnames, zabbix_servers):
    async with aiohttp.ClientSession() as session:
        tasks = [check_host_on_all_servers(session, hostnames, zabbix_server) for zabbix_server in zabbix_servers]
        all_results = await asyncio.gather(*tasks)
        return [result for server_results in all_results for result in server_results]


def read_hostnames_from_file(file_path):
    with open(file_path, 'r') as file:
        hostnames = [line.strip() for line in file.readlines()]
    logging.info(f"Чтение {len(hostnames)} хостов из {file_path}")
    return hostnames


def write_results_to_csv(results, output_file_path):
    with open(output_file_path, 'w', newline='') as csvfile:
        fieldnames = ['hostname', 'zabbix_server']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for result in results:
            writer.writerow(result)
    logging.info(f"Запись в {output_file_path}")


def main():
    hostnames_file = 'hostnames.txt'
    output_file = 'zabbix_hosts_check.csv'

    hostnames = read_hostnames_from_file(hostnames_file)
    results = asyncio.run(check_hosts_in_zabbix_servers(hostnames, zabbix_servers))
    write_results_to_csv(results, output_file)
    print(f"Проверка завершена. Результаты записаны в {output_file}")


if __name__ == '__main__':
    main()
