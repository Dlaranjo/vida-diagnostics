#!/usr/bin/env python3
"""
Script para gerar URLs presignadas para arquivos DICOM processados.
Uso: python generate_url.py <nome-do-arquivo>
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'medical-imaging-pipeline', 'src'))

from delivery.presigned_url_handler import PresignedUrlHandler

def main():
    if len(sys.argv) < 2:
        print("Uso: ./generate_url.sh <caminho-do-arquivo>")
        print("\nExemplos:")
        print("  ./generate_url.sh validated/url-test.dcm")
        print("  ./generate_url.sh processed/WORKING-TEST.dcm")
        print('  ./generate_url.sh "s3://medical-imaging-pipeline-dev-processed-dicom/validated/url-test.dcm"')
        print("\nNota: Use o caminho completo do arquivo no bucket (sem s3://bucket/)")
        sys.exit(1)
    
    filename = sys.argv[1]

    # Remove s3:// prefix if present
    if filename.startswith('s3://'):
        # Extract just the key from s3://bucket/key format
        parts = filename.replace('s3://', '').split('/', 1)
        if len(parts) > 1:
            object_key = parts[1]
        else:
            object_key = filename
    else:
        # Use filename as-is (user provides full path like validated/file.dcm)
        object_key = filename
    
    # Inicializa o handler
    bucket_name = "medical-imaging-pipeline-dev-processed-dicom"
    handler = PresignedUrlHandler(bucket_name=bucket_name)
    
    # Gera URL presignada com validação
    print(f"Gerando URL presignada para: {object_key}")
    print(f"Bucket: {bucket_name}")
    print()
    
    # Verifica se o arquivo existe
    if not handler.validate_object_exists(object_key):
        print(f"❌ ERRO: Arquivo não encontrado no bucket!")
        print(f"\nArquivos disponíveis:")
        import boto3
        s3 = boto3.client('s3')
        response = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            for obj in response['Contents']:
                print(f"  - {obj['Key']}")
        else:
            print("  (nenhum arquivo encontrado)")
        sys.exit(1)
    
    # Gera URL segura (1 hora de expiração por padrão)
    url_info = handler.generate_secure_download_url(
        object_key=object_key,
        expiration_seconds=3600,  # 1 hora
        validate_exists=False  # Já validamos acima
    )
    
    if url_info:
        print("✅ URL gerada com sucesso!")
        print()
        print(f"📥 Download URL:")
        print(url_info['url'])
        print()
        print(f"⏰ Expira em: {url_info['expires_in']} segundos (1 hora)")
        print()
        print("💡 Para baixar o arquivo:")
        print(f"   curl -o {filename.split('/')[-1]} '{url_info['url']}'")
        print()
        print("   Ou abra a URL no navegador para download automático.")
    else:
        print("❌ ERRO: Falha ao gerar URL presignada")
        sys.exit(1)

if __name__ == "__main__":
    main()
