$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path "build" | Out-Null

# Converte o caminho Windows para MSYS2 (ex: C:\foo -> /c/foo)
$rawPath = (Get-Location).Path.Replace('\', '/')
$wd = '/' + $rawPath[0].ToString().ToLower() + $rawPath.Substring(2)

$cmdTestes   = "cd '$wd' && g++ -std=c++20 -O2 -Wall -Wextra -pedantic -static -Isrc testes/testes.cpp src/grafo.cpp -o build/testes.exe"
$cmdDijkstra = "cd '$wd' && g++ -std=c++20 -O2 -Wall -Wextra -pedantic -static -Isrc src/main.cpp src/grafo.cpp -o build/dijkstra.exe -lpsapi"

Write-Host "Compilando testes.exe..."
$proc = Start-Process -FilePath "C:\msys64\usr\bin\bash.exe" `
    -ArgumentList @("-c", $cmdTestes) `
    -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -ne 0) { Write-Host "Erro na compilacao de testes.exe"; exit 1 }

Write-Host "Compilando dijkstra.exe..."
$proc = Start-Process -FilePath "C:\msys64\usr\bin\bash.exe" `
    -ArgumentList @("-c", $cmdDijkstra) `
    -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -ne 0) { Write-Host "Erro na compilacao de dijkstra.exe"; exit 1 }

Write-Host "Compilacao concluida com sucesso."
