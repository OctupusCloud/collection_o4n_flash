#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals


DOCUMENTATION = """
---
module: o4n_flash
version_added: "3.0"
author: "Ed Scrimaglia"
short_description: escanea la flash de un dispositivo de networking
description:
  - Conecta con los dispositivos de networking a vía ssh (netmiko).
  - Explora la flahs.
notes:
  - Testeado en IOS, IOSXE
options:
    user:
        description:
            user para acceder vis ssh al dispositivo de networking
        requerido: True
    host_address:
        description:
            Host IP address del dispositivo de networking
        requerido: True
    password:
        description:
            password para acceder al modo exec al dispositivo de networking via ssh
        requerido: True
    plataforma:
        description:
            tipo de plataforma conforme al parámetro device_type del módulo netmiko
        requerido: True
    flash_device:
        description:
            nombre de la flash en el dispositivo de networking
        values:
            - flash0:, root en flash0
            - flash0:config, directorio config en flash0
        requerido: True
    enable_password:
        description:
            password para acceder al modo privilegiado al dispositivo de networking
        requerido: False
    search:
        description:
            nombre del archivo a verificar su existencia
        values:
            - False: nothing to search
            - file_name: nombre del file a buscar
        requerido: False
    ssh_config:
        description:
            configuracio SSH que usará netmiko
        values:
            - nombre del file incluido el path, que contiene la configuracion SSH
        requerido: False
"""

EXAMPLES = """
tasks:
  - name: Oction Flash Scanning. Option global search (mismo file en todos los dev)
    o4n_flash_dir:
      host_address: "{{ansible_host}}"
      user: "{{ansible_user}}"
      password: "{{ansible_password}}"
      enable_password: "{{ansible_become_password}}"
      plataforma: "{{var_data_model_dev.plataforma}}"
      flash_device: "{{global.container}}"
      search: "{{var_data_model.search_file}}"
      ssh_config: "~/.ssh/config_proxy"
    register: salida

  - name: Oction Flash Scanning. Option dev search (file para cada dev)
    o4n_flash_dir:
      host_address: "{{ansible_host}}"
      user: "{{ansible_user}}"
      password: "{{ansible_password}}"
      enable_password: "{{ansible_become_password}}"
      plataforma: "{{var_data_model_dev.plataforma}}"
      flash_device: "{{device.container}}"
      search: "{{var_data_model_dev.search_file}}"
    register: salida
"""

RETURN = """
case1:
    description: Retorna un objeto JSON cuyo conteniendo sigue el siguiente formato. Ejemplo, file found
    "salida": {
        "Bytes_Free": "xxxxxxx bytes free",
        "Device": "xx.xx.xx.xx",
        "Directorio": "/",
        "Files": {
            "file1": "size1",
            "file2": "size2"
            },
        "Flash": "xxxx",
        "Flash_capacity": "xxxx bytes total",
        "Search": {
            "found": true,
            "searched": "c2900-universalk9-mz.SPA.155-3.M2.bin"
            }
        }
"""

from netmiko import ConnectHandler
from ansible.module_utils.basic import AnsibleModule
from collections import OrderedDict


# Connecto to device
def connectToDevice(_dev_type, _ip, _user, _passw, _sshconf, _enable="", _delayf=.1):
    try:
        if _sshconf != "no":
            fromDevice = ConnectHandler(
                device_type=_dev_type,
                ip=_ip,
                username=_user,
                password=_passw,
                secret=_enable,
                global_delay_factor=_delayf,
                ssh_config_file=_sshconf,
            )
        else:
            fromDevice = ConnectHandler(
                device_type=_dev_type,
                ip=_ip,
                username=_user,
                password=_passw,
                secret=_enable,
                global_delay_factor=_delayf,
            )
        if _enable:
            fromDevice.enable()
        success = True
        ret_msg = "Successful connection"
    except Exception as error:
        ret_msg = "connection error: {}".format(str(error).splitlines())
        success = False
        fromDevice = None

    return fromDevice, ret_msg, success


# Flash content
def outputFlash(_device, _cmd, _ip, _file_to_search, _flash="flash0:"):
    salida_json = OrderedDict()

    try:
        output = _device.send_command(_cmd + " " + _flash)
    except ConnectionError as error:
        ret_msg = "{}Error de conexión: {}".format("\n", error)

    salida = output.splitlines()
    lista_flash_final = list(filter(None, salida))
    salida_json["Device"] = _ip
    salida_json["Flash"] = _flash.strip()
    lista_files = []

    try:
        for elem in lista_flash_final:
            if "directory" in elem.lower():
                salida_json["Directorio"] = elem.split(":")[1].strip()
            elif "bytes total" in elem.lower():
                salida_json["Flash_capacity"] = elem.split(" ")[0].strip()
                salida_json["Bytes_free"] = (
                    elem.split("(")[1].split(" ")[0].strip()
                )
            elif len(elem.split(" ")) >= 8:
                linea_file = elem.split(" ")
                str_list = list(filter(None, linea_file))
                lista_files.append({str_list[8]: str_list[2]})
            else:
                salida_json["unknown"] = elem.strip()
        salida_json["Files"] = lista_files

        # Search file
        search_file = {"searching": _file_to_search}
        search_file["found"] = False
        if _file_to_search not in ['no', 'clean']:
            for object_json in salida_json["Files"]:
                for file_name, file_size in object_json.items():
                    if _file_to_search.strip() == file_name.strip():
                        search_file["found"] = True
                        ret_msg = "scanning flash success and file found"
                    else:
                        search_file["found"] = False
                        ret_msg = "scanning flash success and file not found"
                if search_file["found"] is True:
                    break
            success = True
        else:
            success = True
            ret_msg = "scanning flash success and file searching skipped"
        salida_json["Search"] = search_file
    except IndexError as error:
        success = False
        ret_msg = "scanning flash failed. Error: {}".format(error)

    return salida_json, ret_msg, success


# Main
def main():
    module = AnsibleModule(
        argument_spec=dict(
            host_address=dict(required=True),
            user=dict(required=True),
            password=dict(required=True, no_log=True),
            enable_password=dict(required=True, no_log=True),
            plataforma=dict(requiered=True),
            flash_device=dict(required=True),
            search=dict(required=False),
            delay_factor=dict(requiered=False, type='str', default=".1"),
            ssh_config=dict(requiered=False, type='str', default="no"),
        )
    )

    plataforma = module.params.get("plataforma")
    flash_device = module.params.get("flash_device")
    search = module.params.get("search") if module.params.get("search") not in ['False', 'false', 'no'] else 'no'
    host_address = module.params.get("host_address")
    user = module.params.get("user")
    password = module.params.get("password")
    enable_password = module.params.get("enable_password")
    delay_f = float(module.params.get("delay_factor"))
    sshconf = module.params.get('ssh_config')

    # Establece conexión ssh con el dispisitivo
    device, ret_msg, success_conn = connectToDevice(plataforma, host_address, user, password, sshconf, enable_password, delay_f)

    # escanea contenido de la flash
    if success_conn:
        output, ret_msg, success = outputFlash(device, "dir", host_address, search, flash_device)

    # Dsconecta con el dispositivo
    if success_conn:
        device.disconnect()

    # Retorna valores al playbook
    if success:
        module.exit_json(msg=ret_msg, content=output)
    else:
        module.fail_json(msg=ret_msg)


if __name__ == "__main__":
    main()
