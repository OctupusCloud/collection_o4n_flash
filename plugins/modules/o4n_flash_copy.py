#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

DOCUMENTATION = """
---
module: o4n_flash_copy
version_added: "4.0"
author: "Ed Scrimaglia"
short_description: Copy file desde y hacia la flash de un dispositivo de networking.
description:
  - Conecta con los dispositivos de networking a vía ssh (netmiko).
  - Verifica espacio disponible en la flash.
  - Verifica integridad md5.
  - Copia archivos desde y hacia la flash.
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
            tipo de plataforma
        values:
            netmiko device_type valid values
        requerido: True
    l_path:
        description:
            path del source file
        values:
            - system: path para operacion put
            - no: para operacion get
        requerido: True
    d_path:
        description:
            path del destination file
        values:
            - system: path para operacion get
            - no: para operacion put
        requerido: False
    f_system:
        description:
            nombre de la flash en el dispositivo de networking
        values:
            - flash0, root en flash0
            - flash0:config, directorio config en flash0
        requerido: True
    s_file:
        description:
            nombre del source file
        values:
            - no: no transfer file
            - file_name: nombre de la imagen a transferir
        requerido: True
    d_file:
        description:
            nombre del destination file. Si no se especifica, toma el mismo nombre que el s_file
        values:
            - no: destination file name igual al source file name
            - file_name: nombre del file en el destino
        requerido: False
        default: s_file
    operation:
        description:
            lee y graba files en el device.
        values:
            - get: transfiere file desde el device
            - put: transfiere file hacia el device
        requerido: False
        default: put
    dis_md5:
        description:
            Deshablita el check MD5 sobre el destination file antes de transferir.
        requerido: False
        default: False
    log:
        description:
            Crea Log file o4n_ssh_log@{date}.md segun parametro log_path en Modelo Datos.
        values:
            - yes
            - no
        requerido: False
        default: no
    delay_factor:
        description:
            Factor de delay aplicabe a la session SSH que se establece con los dispositivos. Para la transf de files de 100MB o mas, se recomienda un valor de 2
        values:
            valor decimal comenzando en .1
        requerido: False
        default: .1
    ssh_config:
        description:
            configuracio SSH que usará netmiko
        values:
            - nombre del file incluido el path, que contiene la configuracion SSH
        requerido: False
"""

EXAMPLES = """
tasks:
  - name: Oction Flash copy. Copia file en la flash
      o4n_flash_copy:
        host_address: "{{ansible_host}}"
        user: "{{ansible_user}}"
        password: "{{ansible_password}}"
        enable_password: "{{ansible_become_password}}"
        plataforma: "{{var_data_model_dev.plataforma}}"
        f_system: "{{var_data_model_dev.container}}"
        l_path: "{{var_data_model_dev.local_path}}"
        s_file: "{{var_data_model.search_file}}"
        log: yes
        d_file: file_name
        delay_factor: 2
        ssh_config: "~/.ssh/config_proxy"
      register: salida

  - name: Oction Flash copy. Copia file desde la flash hacia el file system local
      o4n_flash_copy:
        host_address: "{{ansible_host}}"
        user: "{{ansible_user}}"
        password: "{{ansible_password}}"
        enable_password: "{{ansible_become_password}}"
        plataforma: "{{var_data_model_dev.plataforma}}"
        f_system: "{{var_data_model_dev.container}}"
        l_path: "{{var_data_model_dev.local_path}}"
        s_file: "{{var_data_model.search_file}}"
        d_file: file_name
        dis_md5: True
        operation: get
  register: salida
"""

RETURN = """
case1:
    description: Retorna un objeto JSON cuyo conteniendo sigue el siguiente formato. Transfer False
    "salida": {
        "changed": false,
        "failed": false,
        "msg": "File not transferred",
        "std_out": {
            "disk_space": true,
            "file_exists": true,
            "file_name": "test.yaml",
            "file_transferred": false,
            "file_verified": true,
            "md5": "ok",
            "time": "00:02.785901"
            }
        }
case2:
    description: Retorna un objeto JSON cuyo conteniendo sigue el siguiente formato. Transfer True
    "salida": {
        "changed": false,
        "failed": false,
        "msg": "File Transfer done",
        "std_out": {
            "disk_space": true,
            "file_exists": true,
            "file_name": "test.yaml",
            "file_transferred": true,
            "file_verified": true,
            "md5": "fail",
            "time": "00:02.999014"
            }
        }
"""

# Modulos
import netmiko
from datetime import datetime
from dateutil import tz
from ansible.module_utils.basic import AnsibleModule
import logging


# Global variables

# Funciones
def connectToDevice(_dev_type, _ip, _user, _passw, _sshconf, _enable="", _delayf=.1):
    try:
        ret_msg = ""
        if _sshconf != "no":
            fromDevice = netmiko.ConnectHandler(
                device_type=_dev_type,
                ip=_ip,
                username=_user,
                password=_passw,
                secret=_enable,
                global_delay_factor=_delayf,
                ssh_config_file=_sshconf
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


# String to Bool
def str2bool(_v):
    return _v.lower() in ["yes", "true", "1", "t"]


# Logica de transferencia
def tranfer_logic(_scp_transfer, _operation, _dmd5, _lpath, _sfile, _dpath, _dfile, _fsystem, _rep_lpath, _rep_sfile,
                  _rep_dpath, _rep_dfile):
    try:
        if _scp_transfer.verify_space_available():
            if not _scp_transfer.check_file_exists():
                if _operation == "put":
                    _scp_transfer.transfer_file()
                elif _operation == "get":
                    _scp_transfer.get_file()
                salida = {'lpath': _rep_lpath, 'sfile': _rep_sfile, 'dpath': _rep_dpath, 'dfile': _rep_dfile,
                          'file_exists': False,
                          'file_transferred': True, 'file_verified': not _dmd5,
                          'md5': 'avoided', 'disk_space': True}
                ret_msg = "File Transfer done"
            else:
                if _dmd5 is True:
                    salida = {'lpath': _rep_lpath, 'sfile': _rep_sfile, 'dpath': _rep_dpath, 'dfile': _rep_dfile,
                              'file_exists': True,
                              'file_transferred': False, 'file_verified': False,
                              'md5': 'avoided', 'disk_space': "Ok"}
                    ret_msg = "File not transferred"
                else:
                    if _scp_transfer.compare_md5():
                        salida = {'lpath': _rep_lpath, 'sfile': _rep_sfile, 'dpath': _rep_dpath, 'dfile': _rep_dfile,
                                  'file_exists': True,
                                  'file_transferred': False, 'file_verified': not _dmd5,
                                  'md5': 'Ok', 'disk_space': "Ok"}
                        ret_msg = "File not transferred"
                    else:
                        _scp_transfer.transfer_file()
                        salida = {'lpath': _rep_lpath, 'sfile': _rep_sfile, 'dpath': _rep_dpath, 'dfile': _rep_dfile,
                                  'file_exists': True,
                                  'file_transferred': True, 'file_verified': not _dmd5,
                                  'md5': 'Fail', 'disk_space': "Ok"}
                        ret_msg = "File Transfer done"
        else:
            salida = {'lpath': _rep_lpath, 'sfile': _rep_sfile, 'dpath': _rep_dpath, 'dfile': _rep_dfile,
                      'file_exists': False,
                      'file_transferred': False, 'file_verified': False, 'disk_space': "Fail"}
            ret_msg = "File not transferred"
        success = True
    except Exception as error:
        success = False
        ret_msg = "File Transfer has Failed, error {}".format(error)
        salida = {'lpath': _rep_lpath, 'sfile': _rep_sfile, 'dpath': _rep_dpath, 'dfile': _rep_dfile,
                  'file_exists': False,
                  'file_transferred': False, 'file_verified': False, 'disk_space': False}
    return salida, success, ret_msg


# Transferencia
def transfer(_ssh_conn, _sfile, _dfile, _fsystem, _operacion, _lpath, _dpath, _dmd5=False, _ovfile=True):
    source_file = (_lpath + "/" + _sfile) if _lpath not in ['no', ""] else _sfile
    dest_file = (_dpath + "/" + _dfile) if _dpath not in ['no', ""] else _dfile
    # valores para preparar el json de salida del modulo
    rep_sfile = _sfile
    if _operacion == "get":
        rep_lpath = _lpath if _lpath not in ["no", ""] else _fsystem + "/"
        rep_dpath = _dpath if _dpath not in ["no", ""] else "/"
    elif _operacion == "put":
        rep_lpath = _lpath + "/" if _lpath not in ["no", ""] else "/"
        rep_dpath = _fsystem + _dpath + "/" if _dpath not in ["no", ""] else _fsystem + "/"
    rep_dfile = _dfile
    try:
        scp_transfer = netmiko.FileTransfer(
            _ssh_conn, source_file=source_file, dest_file=dest_file, file_system=_fsystem, direction=_operacion
        )
        start = datetime.now()
        scp_transfer.establish_scp_conn()
        if _operacion == "put":
            salida, success, ret_msg = tranfer_logic(scp_transfer, "put", _dmd5, _lpath, _sfile, _dpath, _dfile,
                                                     _fsystem, rep_lpath,
                                                     rep_sfile, rep_dpath, rep_dfile)

        elif _operacion == "get":
            salida, success, ret_msg = tranfer_logic(scp_transfer, "get", _dmd5, _lpath, _sfile, _dpath, _dfile,
                                                     _fsystem, rep_lpath,
                                                     rep_sfile, rep_dpath, rep_dfile)

        stop = datetime.now()
        salida["time"] = "{}".format(stop - start)
    except Exception as error:
        success = False
        ret_msg = "File Transfer Call has Failed, error {}".format(error)
        salida = {"local path": rep_lpath, "source file": rep_sfile, "destination path": rep_dpath,
                  "destination file": rep_dfile}

    return salida, success, ret_msg


# Create Log File
def write_log_file():
    # Set Time Zone
    from_zone = tz.gettz('UTC')
    to_zone = tz.gettz('America/Argentina/Buenos_Aires')
    fecha_utc = datetime.utcnow()
    fecha_utc = fecha_utc.replace(tzinfo=from_zone)
    fecha_local = fecha_utc.astimezone(to_zone)
    # Set date & Time
    fecha = fecha_local.strftime("%Y-%m-%d , %H:%M:%S")
    # Create Log File Name
    log_file = f"o4n_ssh_log@{fecha}.log"
    log_path = "./documentacion/"
    create_log = log_path + log_file

    # Write Log File
    logging.basicConfig(filename=create_log, level=logging.DEBUG)
    # logger = logging.getLogger("netmiko")


# Main
def main():
    success = False
    output = {}
    ret_msg = ""
    module = AnsibleModule(
        argument_spec=dict(
            host_address=dict(required=True),
            user=dict(required=True),
            password=dict(required=True, no_log=True),
            enable_password=dict(required=True, no_log=True),
            plataforma=dict(required=True),
            l_path=dict(required=True),
            d_path=dict(required=False, type='str', default="no"),
            f_system=dict(required=True),
            s_file=dict(required=True),
            d_file=dict(requiered=False, type='str', default="no"),
            operation=dict(requiered=False, type='str', default="put"),
            dis_md5=dict(requiered=False, type='str', choices=["True", "true", "False", "false"], default="False"),
            delay_factor=dict(requiered=False, type='str', default=".1"),
            log=dict(requiered=False, type='str', default="no"),
            ssh_config=dict(requiered=False, type='str', default="no"),
        )
    )
    lpath = module.params.get("l_path") if module.params.get("l_path") not in ['False', 'false', 'no'] else 'no'
    dpath = module.params.get("d_path") if module.params.get("d_path") not in ['False', 'false', 'no'] else 'no'
    sfile = module.params.get("s_file") if module.params.get("s_file") not in ['False', 'false', 'no', ""] else 'no'
    sshconf = module.params.get("ssh_config")
    dfile = module.params.get("d_file") if module.params.get("d_file") not in ['False', 'false', 'no', ""] else sfile
    create_log = str2bool(module.params.get("log"))
    fsystem = module.params.get("f_system")
    operacion = module.params.get("operation")
    disable_md5 = str2bool(module.params.get("dis_md5"))
    delay_f = float(module.params.get("delay_factor"))
    plataforma = module.params.get("plataforma")
    host_address = module.params.get("host_address")
    user = module.params.get("user")
    password = module.params.get("password")
    enable_password = module.params.get("enable_password")

    # Create Log File
    if create_log:
        write_log_file()

    # Establece conexión ssh con el dispisitivo
    if sfile not in ['no']:
        device, ret_msg, success_conn = connectToDevice(
            plataforma, host_address, user, password, sshconf, enable_password, delay_f
        )

        # Transferencias hacia y desde el dispositivo
        if success_conn:
            output, success, ret_msg = transfer(
                device, sfile, dfile, fsystem, operacion.lower(), lpath, dpath, disable_md5
            )

        # Dsconección
        if success_conn:
            device.disconnect()
    else:
        ret_msg = "No file to transfer"
        success = True
        output = {
            "file_name": "No file to transfer",
            "lpath": False,
            "dpath": False,
            "dfile": False,
            "file_exists": False,
            "file_transferred": False,
            "file_verified": False,
            "md5": "avoided",
            "disk_space": False,
        }

    # Retorna valores al playbook
    if success:
        module.exit_json(msg=ret_msg, std_out=output)
    else:
        module.fail_json(msg=ret_msg, std_out=output)


if __name__ == "__main__":
    main()
