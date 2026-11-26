$ErrorActionPreference = "Continue"

New-Item -ItemType Directory -Force -Path "build" | Out-Null

if (-not (Get-Command g++ -ErrorAction SilentlyContinue)) {
    Write-Host "Erro: g++ nao encontrado no PATH (esperado em C:\msys64\ucrt64\bin)"
    exit 1
}

function Compilar($saida, $fontes, $extra) {
    Write-Host "Compilando $saida..."
    $global:LASTEXITCODE = 1
    & g++ -std=c++20 -O2 -Wall -Wextra -pedantic -static -Isrc @fontes -o $saida @extra 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Erro na compilacao de $saida"
        exit 1
    }
}

Compilar "build\testes.exe"   @("testes\testes.cpp", "src\grafo.cpp") @()
Compilar "build\dijkstra.exe" @("src\main.cpp", "src\grafo.cpp")      @("-lpsapi")
Compilar "build\gerador.exe"  @("src\gerador.cpp")                    @()

Write-Host "Compilacao concluida com sucesso."
