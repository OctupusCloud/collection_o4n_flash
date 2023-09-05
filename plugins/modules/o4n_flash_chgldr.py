#!usr/local/bin/python3
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

DOCUMENTATION = """
---
module: o4n_flash_chgldr
version_added: "2.0"
author: "Ed Scrimaglia"
short_description: Change boot loader in IOS and IOSXE configuration
description:
  - Conecta con los dispositivos de networking a vía ssh (netmiko).
  - cambia registro de booting
notes:
  - Testeado en IOS, IOSXE
options:
    host_address:
        description:
            Host IP address del dispositivo de networking 
        requerido: True
    user:
        description:
            Usuario para acceder via ssh al dispositivo de networking 
        requerido: True
    password:
        description:
            Contraseña para acceder via ssh al dispositivo de networking 
        requerido: True
    enable_password:
        description:
            Contraseña "enable" para acceder via ssh al dispositivo de networking 
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
    chg_loader:
        description:
            nombre imagen desde la cual iniciará el dispositivo de networking
        values:
            - False: nada que cambiar
            - name_ldr: nombre de la imagen
            - clean: se borran todos los registro tipo 'boot system flash'
        requerido: True
    ssh_config:
        description:
            configuracio SSH que usará netmiko
        values:
            - nombre del file incluido el path, que contiene la configuracion SSH
        requerido: False
"""

EXAMPLES = """
tasks:
  - name: Oction Flash Chg_ldr. Cambia registro de booting
    o4n_flash_chgldr:
        host_address: "{{ansible_host}}"
        user: "{{ansible_user}}"
        password: "{{ansible_password}}"
        enable_password: "{{ansible_become_password}}"
        plataforma: "{{var_data_model_dev.plataforma}}"
        flash_device: "{{global.container}}"
        chg_loader: image_name
        ssh_config: "~/.ssh/config
    register: salida

  - name: Oction Flash Chg_ldr. Clean registro de booting
    o4n_flash_chgldr:
        host_address: "{{ansible_host}}"
        user: "{{ansible_user}}"
        password: "{{ansible_password}}"
        enable_password: "{{ansible_become_password}}"
        plataforma: "{{var_data_model_dev.plataforma}}"
        flash_device: "{{global.container}}"
        chg_loader: clean
    register: salida

  - name: Oction Flash Chg_ldr. Nothing to change
    o4n_flash_chgldr:
        host_address: "{{ansible_host}}"
        user: "{{ansible_user}}"
        password: "{{ansible_password}}"
        enable_password: "{{ansible_become_password}}"
        plataforma: "{{var_data_model_dev.plataforma}}"
        chg_loader: False
    register: salida
"""

RETURN = """
msg:
    {
        {
            description: Retorna un objeto JSON cuyo conteniendo sigue el siguiente formato.
            salida: {
                "changed": false,
                "failed": false,
                "msg": "Boot loader changed",
                "std_out": {
                    "loader": "boot system flash XXXXX",
                }
            }
        },
        {
            description: Retorna un objeto JSON cuyo conteniendo sigue el siguiente formato.
            salida: {
                "changed": false,
                "failed": false,
                "msg": "Boot loader register cleaned",
                "std_out": {
                    "loader": "Boot register cleaned",
                }
            }
        }
    }

"""

# Modulos
import netmiko
from ansible.module_utils.basic import AnsibleModule
import json
from collections import OrderedDict


# Global variables

# Connect to device
def connectToDevice(_dev_type, _ip, _user, _passw, _shhconf, _enable="", _delayf=.1):
    try:
        if _shhconf != "no":
            fromDevice = netmiko.ConnectHandler(
                device_type=_dev_type,
                ip=_ip,
                username=_user,
                password=_passw,
                secret=_enable,
                global_delay_factor=_delayf,
                ssh_config_file=_shhconf,
            )
        else:
            fromDevice = netmiko.ConnectHandler(
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


# Send config command
def config_command(_device, _cmd):
    try:
        _device.send_config_set(_cmd)
        success = True
        ret_msg = "Command executed"
    except Exception as error:
        ret_msg = "Command not executed, error {} ".format(error)
        success = False
    return success, ret_msg


# Save configuration
def save_config(_device):
    _device.save_config()


# String to Bool
def str2bool(_v):
    return _v.lower() in ["yes", "true", "1", "t"]


# Flash content
def outputFlash(_device, _cmd, _ip, _file_to_search, _flash="flash0:"):
    salida_json = OrderedDict()
    lista_flash_final = []
    lista_files = []
    ret_msg = ""
    try:
        output = _device.send_command(_cmd + " " + _flash)
        salida = output.splitlines()
        lista_flash_final = list(filter(None, salida))
        salida_json["Device"] = _ip
        salida_json["Flash"] = _flash.strip()
    except ConnectionError as error:
        ret_msg = "{}Error de conexión: {}".format("\n", error)

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
                if search_file["found"] == True:
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


# Find Boot system command in running-config
def boot_system_exists(_device, _cmd, _line_content):
    line_exist = False
    success = False
    try:
        output = _device.send_command(_cmd, use_genie=True)
        if _line_content in output:
            line_exist = True
        ret_msg = "Boot system command found"
        success = True
    except ConnectionError as error:
        ret_msg = ("{}, error de conexión".format(error))
    except TypeError as error:
        ret_msg = ("{}, error de tipo".format(error))
    except Exception as error:
        ret_msg = ("{}, error de proceso".format(error))

    return line_exist, success, ret_msg


# Change boot system command
def chgLoader(_device, _image, _plataforma, _cmd):
    output = {"loader": "Platform " + _plataforma + " is not supported"}
    success = False
    cmds = []
    ret_msg = "empty"
    try:
        if _image not in ['clean']:
            if _plataforma in ["cisco_ios", "cisco_iosxe"]:
                cmds = [
                    "no boot system",
                    _cmd + _image,
                ]

                # Change boot system command
                success_l = config_command(_device, cmds)
                if success_l:
                    output["loader"] = _cmd +  _image
                    save_config(_device)
                    ret_msg = "Boot loader changed"
                    success = True
                else:
                    ret_msg = "Boot loader not changed"
                    output["loader"] = "Error changing loader"
            else:
                ret_msg = "IOS {} is not supported".format(_plataforma)
        elif _image == 'clean':
            success_l = config_command(_device, "no boot system")
            if success_l:
                output["loader"] = "no boot system"
                save_config(_device)
                success = True
                ret_msg = "Boot loader register cleaned"
        else:
            output["loader"] = False
            ret_msg = "Boot record not changed"
    except Exception as error:
        ret_msg = "Boot loader change has failed, error {}".format(error)
        output["loader"] = False
        
    return ret_msg, success, output


# Main
def main():
    success = False
    module = AnsibleModule(
        argument_spec=dict(
            host_address=dict(required=True),
            user=dict(required=True),
            password=dict(required=True,no_log=True),
            enable_password=dict(required=True,no_log=True),
            plataforma=dict(required=True),
            flash_device=dict(required=True),
            chg_loader=dict(requiered=True),
            delay_factor=dict(requiered=False, type='str', default=".1"),
            ssh_config=dict(requiered=False, type='str', default="no"),
        )
    )

    change_boot_loader = module.params.get("chg_loader")
    loader_param_parsed = change_boot_loader.replace("'", '"')
    loader_param_json = json.loads(loader_param_parsed)
    image = loader_param_json.get("boot_image") if loader_param_json.get("boot_image") not in \
                                                   ['False', 'false', 'no', ""] else "no"
    boot_cmd = loader_param_json.get("boot_system_cmd")
    plataforma = module.params.get("plataforma")
    flash_device = module.params.get("flash_device")
    host_address = module.params.get("host_address")
    user = module.params.get("user")
    password = module.params.get("password")
    enable_password = module.params.get("enable_password")
    delay_f = float(module.params.get("delay_factor"))
    shhconf=module.params.get("ssh_config")

    # Establece conexión ssh con el dispisitivo
    output = {}
    success = True
    if image not in ['no']:
        device, ret_msg, success_conn = connectToDevice(
            plataforma, host_address, user, password, shhconf, enable_password, delay_f
        )
        if success_conn:
            if image not in ['clean']:
                # verifica image exist on flash
                salida_json, ret_msg, success = outputFlash(device, "dir", host_address, image, flash_device)
                if str2bool(str(salida_json["Search"]["found"])):
                    # Cambia boot loader
                    ret_msg, success, output = chgLoader(device, image, plataforma, boot_cmd)
                else:
                    ret_msg = "Boot loader change has failed, image does not exist"
                    success = False
            else:
                # Clean boot loader
                ret_msg, success, output = chgLoader(device, image, plataforma, boot_cmd)
        else:
            success = False
    else:
        output["loader"] = "Boot loader not changed"
        ret_msg = "No change requirement"
        success_conn = False

    # Dsconección
    if success_conn:
        device.disconnect()

    # Retorna valores al playbook
    if success:
        module.exit_json(msg=ret_msg, std_out=output)
    else:
        module.fail_json(msg=ret_msg)


if __name__ == "__main__":
    main()