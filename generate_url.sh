#!/bin/bash
# Script para gerar URLs presignadas para arquivos DICOM processados
# Uso: ./generate_url.sh <nome-do-arquivo>

# Ativa o ambiente virtual
source medical-imaging-pipeline/venv/bin/activate

# Executa o script Python
python3 generate_url.py "$@"

# Desativa o ambiente virtual
deactivate
