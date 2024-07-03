#!/bin/bash
echo "Iniciando proceso"

# Bloque Try
{
    cf login -a https://api.cf.br10.hana.ondemand.com -u "" -p "" -o SCP_CyT_app-devqa-cii-cf-sp -s tesistas
    cf push capstonebackendlourdes
} || {
    # Bloque Catch
    echo "Ocurrió un error durante el proceso de despliegue"
}

echo "Fin del proceso"
