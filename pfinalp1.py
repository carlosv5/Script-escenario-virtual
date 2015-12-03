#!/usr/bin/python
'''
Script para la generacion del escenario de la practica 3
'''
import os
import sys
import re
import subprocess
import time
#from pprint import pprint
from	lxml	import	etree	

#Array de maquinas. Tendremos que tratarlas de distinta manera
machines = ["c1","lb","s1","s2","s3", "s4", "s5"]

#Leyenda machinesIP : nombreMaquina,[address, netmask,network,broadcast,gateway] 
machinesIP = { "c1":{"eth0":["10.0.1.2", "255.255.255.0","10.0.1.0","10.0.1.255","10.0.1.1"]},
               "lb":{"eth0":["10.0.1.1", "255.255.255.0","10.0.1.0","10.0.1.255",None],
                     "eth1":["10.0.2.1", "255.255.255.0","10.0.2.0","10.0.2.255",None]
                },
               "s1":{"eth0":["10.0.2.11", "255.255.255.0","10.0.2.0","10.0.2.255","10.0.2.1"]},
               "s2":{"eth0":["10.0.2.12", "255.255.255.0","10.0.2.0","10.0.2.255","10.0.2.1"]},
               "s3":{"eth0":["10.0.2.13", "255.255.255.0","10.0.2.0","10.0.2.255","10.0.2.1"]},
               "s4":{"eth0":["10.0.2.14", "255.255.255.0","10.0.2.0","10.0.2.255","10.0.2.1"]},
               "s5":{"eth0":["10.0.2.15", "255.255.255.0","10.0.2.0","10.0.2.255","10.0.2.1"]},
}


def create(parametro):
    '''
    Metodo para crear las imagenes qcow2 y los xml de las maquinas.
    Ademas de la creacion de las LAN
    '''
    for i in range (0, parametro + 2):
        createOne(machines[i])

    #Creamos las LAN si no estan creadas

    if(os.system("ifconfig | grep -w LAN1 > /dev/null") != 0) :
        os.system('sudo brctl addbr LAN1')
        os.system('sudo ifconfig LAN1 up')
    else:
        print "..... LAN1 ya creada y en estado up"

    if(os.system("ifconfig | grep -w LAN2 > /dev/null") != 0) :
        os.system('sudo brctl addbr LAN2')
        os.system('sudo ifconfig LAN2 up')
    else:
        print "..... LAN2 ya creada y en estado up"

    #Incluimos al host en el escenario si no esta incluido

    if(os.system("ifconfig | grep -w 10.0.1.3 > /dev/null") != 0) :
        os.system("sudo ifconfig LAN1 10.0.1.3/24")
        os.system("sudo ip route add 10.0.0.0/16 via 10.0.1.1")
    else:
        print "..... El host ya esta incluido en el escenario"


def createOne(machine):
    
    if not isCreated(machine): 
        #Cargamos el fichero xml    
        tree = etree.parse('plantilla-vm-p3.xml')    
  
        #Cambio a nombre de la maquina
        root    =    tree.getroot()    
        name    =    root.find("name")    
        name.text = machine   

        #Cambio de ubicacion
        source=root.find("./devices/disk/source")    
        path = os.getcwd()    
        source.set("file",path+"/"+machine+".qcow2")    

        #Creamos la imagen qcow2
        os.system('qemu-img create -f qcow2 -b cdps-vm-base-p3.qcow2 '+machine+'.qcow2')

        #Cambiamos la interface
        if(machine != "c1"):
            #SX: hay que ponerles LAN2
            source=root.find("./devices/interface/source")    
            source.set("bridge","LAN2")
            #LB hay que ponerle una nueva etiqueta
            if(machine == "lb"):
                devices=root.find("./devices")    
                devices.insert(2, etree.Element("interface"))
                interface=root.find("./devices/interface")
                interface.set("type","bridge")
                interface.append(etree.Element("source"))
                interface.append(etree.Element("model"))
                source=root.find("./devices/interface/source")
                source.set("bridge","LAN1")
                model=root.find("./devices/interface/model")
                model.set("type","virtio")
        else:
            #C1: hay que ponerle LAN1
            source=root.find("./devices/interface/source")    
            source.set("bridge","LAN1")
 
        #Imprimir el xml con todos los cambios    
        #print    etree.tostring(tree,pretty_print=True)    
  
        #Escrimos en un nuevo fichero
        f = open (machine+".xml", "w")
        f.write(etree.tostring(tree,pretty_print=True))
        f.close()
        print "..... Creada la maquina: %s" % machine
    else:
        print ("..... Ya has creado alguno de los archivos de %s. Haz un destroy para poder crearlas." %machine)


def start(parametro):
    '''
    Metodo para poner a correr las maquinas pedidas
    '''
    for i in range (0, parametro + 2):
        startOne(machines[i])

        
def startOne(machine):
    '''
    Metodo para poner a correr una maquina pasada como parametro
    '''
    if(not isRunning(machine)):
        #
        # Mount
        #
        os.system("mkdir mnt")
        actualPath = os.getcwd()
        pathMnt = os.path.join(actualPath,"mnt")    
        cmd = "sudo vnx_mount_rootfs -s -r %s.qcow2 %s" % (machine, pathMnt)
        os.system(cmd)

        #
        # Hostname
        #
        pathHostname = os.path.join(pathMnt,"etc/hostname")
        cmd = "echo %s > %s " % (machine,pathHostname)
        os.system(cmd)
       
        #
        # Interfaces
        #
        pathInterfaces = os.path.join(pathMnt,"etc/network/interfaces")

        #
        # eth0
        #   
        if(machinesIP[machine].has_key("eth0")):
            f = open(pathInterfaces,"w")
            string = "auto lo\niface lo inet loopback\n\nauto eth0\niface eth0 inet static\naddress " + machinesIP[machine]["eth0"][0]+ "\nnetmask "+ machinesIP[machine]["eth0"][1]+ "\nnetwork "+ machinesIP[machine]["eth0"][2]+ "\nbroadcast "+ machinesIP[machine]["eth0"][3]+ "\n"
            if machinesIP[machine]["eth0"][4] != None:
                string = string + "gateway "+ machinesIP[machine]["eth0"][4]+ "\n"
            f.write(string)
            f.close()

        #
        # eth1. (Solo lb)
        #
        if(machinesIP[machine].has_key("eth1")):
            f = open(pathInterfaces ,"a")
            string = "auto eth1\niface eth1 inet static\naddress " + machinesIP[machine]["eth1"][0]+ "\nnetmask "+ machinesIP[machine]["eth1"][1]+ "\nnetwork "+ machinesIP[machine]["eth1"][2]+ "\nbroadcast "+ machinesIP[machine]["eth1"][3]
            if machinesIP[machine]["eth1"][4] != None:
                string = string + "\ngateway "+machinesIP[machine]["eth1"][4]+ "\n"
            f.write(string)
            f.close()
            #Se pone a 1 el ip_forward para que encamine
            pathSysctl = os.path.join(pathMnt,"etc/sysctl.conf")
            if(os.system("sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' %s" % pathSysctl) != 0):     
                print "..... Error cambiando el ip_forward"                 
                sys.exit(1)

        #
        # Unmount
        #
        cmd = "sudo vnx_mount_rootfs -u mnt"
        if os.system(cmd) != 0:
            print "..... Error corriendo el comando: %s" % cmd
            if os.system(cmd) != 0:
                print "..... Error DOBLE corriendo el comando: %s" % cmd
                sys.exit(1)
            
        if(subprocess.call(["sudo","virsh","create",machine+".xml"]) != 0):
            subprocess.call(["sudo","virsh","create",machine+".xml"])
        #Forma grafica
        os.system("virt-viewer " + machine + "&")
        print "..... Arrancada la maquina: %s" % machine
    else:
        print "..... La maquina %s ya esta arrancada" % machine


def stop(parametro):
    '''
    Metodo para parar las maquinas
    '''
    for i in range (0, parametro + 2):
        stopOne(machines[i])


def stopOne(machine):
    '''
    Metodo para parar la maquina que se pasa como parametro
    '''
    if(isRunning(machine)): 
        os.system("sudo virsh shutdown " + machine )
        print "..... Parada la maquina %s" % machine
    else:
        print "..... La maquina %s no estaba corriendo" % machine            


def stopDestroy(parametro):
    '''
    Metodo para parar las maquinas
    '''
    for i in range (0, parametro + 2):
        stopDestroyOne(machines[i])


def stopDestroyOne(machine):
    '''
    Metodo para parar la maquina que se pasa como parametro
    '''
    if(isRunning(machine)): 
        os.system("sudo virsh destroy " + machine )
        print("..... Parada destructivamente la maquina %s" % machine) 
    else:
        print("..... La maquina %s no estaba corriendo" % machine)           		
    	


def monitor(parametro):
    '''
    Metodo que devuelve las estadisticas de las maquinas
    '''
    for i in range (0, parametro + 2):
        monitorOne(machines[i])
    
def monitorOne(machine):
    '''
    Metodo que devuelve las estadisticas de una maquina que se pasa como parametro
    '''   
    if(isRunning(machine)):		
        print "%s" % "*" * 120
        print "Estadisticas de la maquina %s" % machine
        print "%s" % "*" * 120
        print "%s" % "=" * 52
        print "domstate:"
        print "%s" % "=" * 52
        os.system("sudo virsh domstate %s" % machine)
        print "%s" % "=" * 52
        print "cpu-stats:"
        print "%s" % "=" * 52
        os.system("sudo virsh cpu-stats %s" % machine)
        print "%s" % "=" * 52
        print "dominfo:"
        print "%s" % "=" * 52
        os.system("sudo virsh dominfo %s" % machine)
    else:
        print("..... La maquina %s no esta arrancada" % machine)


def destroy(parametro):
    '''
    Metodo para eliminar los ficheros de las maquinas
    '''	
    for i in range (0, parametro + 2):
        destroyOne(machines[i]) 


def destroyOne(machine):
    '''
    Metodo para eliminar los ficheros de una maquina que se pasa como parametro
    '''    
        
    if isCreated(machine):
        os.system("rm -f " + machine + ".qcow2 ") 
        os.system("rm -f " + machine + ".xml ")
        print "..... Destruidos los ficheros de la maquina %s" % machine
    else: 
        print "..... La maquina %s no estaba creada" % machine


def help():
    '''
    Ayuda para usar nuestro script
    '''
    print "\npython pfinalp1 [funcion] [nServidores]"
    print "Funciones para arrancar el escenario: create, start, stop, destroy, monitor, stopDestroy"
    print "nServidores: 1-5"

    print "\npython pfinalp1 [funcionOne] [nombreMaquina]"
    print "Funciones para arrancar una maquina: createOne, startOne, stopOne, destroyOne, stopDestroyOne, monitorOne"
    print "nombreMaquina: c1, lb, s1, s2, s3, s4, s5"

    sys.exit(1)



def error(parametro):	
    '''
    Metodo que trata los errores de funciones
    '''
    if parametro == "funcion":
        print "!!!!! Has introducido una funcion inexistente, consulta help para ver las funciones disponibles."
    else:
        print "!!!!! Comprueba que hayas introducido el numero de servidores tras la accion a realizar. El numero permitido de servidores es de 1-5"
    sys.exit(1)


def isRunning(machine):
    '''
    Metodo para ver si esta corriendo esa maquina
    '''
    if(os.system("sudo virsh list | grep -w %s > /dev/null" % machine) == 0):
        return True
    else:
        return False

def isCreated(machine):
    '''
    Metodo para ver si esta creada una maquina
    '''
    if os.system('ls ./ | grep -w ' + machine + '.xml > /dev/null') == 0 and os.system('ls ./ | grep -w ' + machine + '.qcow2 > /dev/null') == 0: 
        return True
    else:
        return False


def checkParameters(numero):
    '''
    Metodo para comprobacion del numero pasado
    '''
    if (len(sys.argv) < 4 and len(sys.argv) > 2 and numero < 6 and numero > 0):
        return numero
    else:
        error("numero")


def main():
    '''
    Proceso principal del script
    '''
    #Comprobacion de parametros
    if(len(sys.argv) == 1):
        help()

    #Comprobacion de la funcion que se pasa y el parametro introducido
    #Si la funcion es para arrancar todo el escenario, comprobaremos que el parametro es un numero entre 1-5    
    if(sys.argv[1] == "create" or sys.argv[1] == "start" or sys.argv[1] == "stop" or\
            sys.argv[1] == "stopDestroy" or sys.argv[1] == "destroy" or\
            sys.argv[1] == "monitor" or sys.argv[1] == "help"):
        try:
            numServ = checkParameters(int(sys.argv[2]))
        except IndexError:
            help()
        except ValueError:
            print "Tienes que introducir un numero"
            help()
        if (sys.argv[1] == "create"):
            create(numServ)
        elif(sys.argv[1] == "start"):
            start(numServ)
        elif(sys.argv[1] == "stop"):
            stop(numServ)
        elif(sys.argv[1] == "stopDestroy"):
            stopDestroy(numServ)
        elif(sys.argv[1] == "destroy"):
            destroy(numServ)
        elif(sys.argv[1] == "monitor"):
            monitor(numServ)
        elif(sys.argv[1] == "help"):
            help()

    #Si la funcion es para arrancar una sola maquina, comprobaremos que el parametro es una de las maquinas posibles    
    elif(sys.argv[1] == "createOne" or sys.argv[1] == "startOne" or sys.argv[1] == "stopOne" or\
            sys.argv[1] == "stopDestroyOne" or sys.argv[1] == "destroyOne" or sys.argv[1] == "monitorOne"):         
        if(sys.argv[2] == "c1" or sys.argv[2] == "lb" or sys.argv[2] == "s1" or sys.argv[2] == "s2" or\
                sys.argv[2] == "s3" or sys.argv[2] == "s4" or sys.argv[2] == "s5"): 
     
            if (sys.argv[1] == "createOne"):
                createOne(sys.argv[2])
            elif(sys.argv[1] == "startOne"):
                startOne(sys.argv[2])
            elif(sys.argv[1] == "stopOne"):
                stopOne(sys.argv[2])
            elif(sys.argv[1] == "stopDestroyOne"):
                stopDestroyOne(sys.argv[2])
            elif(sys.argv[1] == "destroyOne"):
                destroyOne(sys.argv[2])
            elif(sys.argv[1] == "monitorOne"):
                monitorOne(sys.argv[2])
            else:
                error("funcion")
        else:
            print "!!!!! Tienes que introducir alguna de las maquinas posibles: c1, lb, s1, s2, s3, s4, s5"
            help()

    #Si la funcion no esta entre las definidas damos un error
    else:
        error("funcion")
                
#Llamada al proceso principal

main()



