#!/usr/bin/env python3
"""
Script simples para criar executável do Chord Importer usando PyInstaller.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Execute um comando e mostra o resultado."""
    print(f"\nExecutando: {description}...")
    print(f"Comando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"OK {description} concluido com sucesso!")
        if result.stdout:
            print("Output:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERRO em {description}:")
        print("STDERR:", e.stderr)
        if e.stdout:
            print("STDOUT:", e.stdout)
        return False

def main():
    """Função principal do script de build."""
    print("Chord Importer - Build Script Simples")
    print("=" * 50)
    
    # Verificar se estamos no diretório correto
    if not os.path.exists("chord_importer"):
        print("ERRO: Diretorio 'chord_importer' nao encontrado!")
        print("Execute este script na raiz do projeto.")
        return False
    
    # Limpar diretórios anteriores
    print("\nLimpando diretorios anteriores...")
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  Removido: {dir_name}")
    
    # Comando PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=ChordImporter",
        "--windowed",  # GUI app (sem console)
        "--onedir",    # Diretório ao invés de arquivo único
        "--clean",
        "--noconfirm",
        "--add-data=chord_importer;chord_importer",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=numpy",
        "--hidden-import=pyaudio",
        "--hidden-import=requests",
        "--hidden-import=beautifulsoup4",
        "--hidden-import=playwright",
        "chord_importer/__main__.py"
    ]
    
    # Executar build
    if not run_command(cmd, "Build do executavel"):
        return False
    
    # Verificar se foi criado
    exe_path = "dist/ChordImporter/ChordImporter.exe"
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\nSUCESSO! Executavel criado: {exe_path}")
        print(f"Tamanho: {size_mb:.1f} MB")
        
        # Criar arquivo de instruções
        instructions = """
# Chord Importer - Executavel

## Como usar:
1. Navegue ate a pasta 'dist/ChordImporter/'
2. Execute 'ChordImporter.exe'

## Funcionalidades:
- Afinador de guitarra com deteccao automatica
- Busca de cifras no CifraClub  
- Busca por sequencia de acordes
- Export para PDF e XML
- Selecao de microfone
- Sistema de log

## Requisitos:
- Windows 10+
- Microfone para afinador
- Internet para busca de cifras
"""
        
        with open("dist/INSTRUCOES.txt", "w", encoding="utf-8") as f:
            f.write(instructions)
        
        print("Arquivo INSTRUCOES.txt criado em dist/")
        return True
    else:
        print("ERRO: Executavel nao foi criado!")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n" + "="*50)
        print("BUILD CONCLUIDO COM SUCESSO!")
        print("Executavel disponivel em: dist/ChordImporter/")
        print("="*50)
    sys.exit(0 if success else 1)
