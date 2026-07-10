param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8768
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
python (Join-Path $Here "server.py") --host $HostName --port $Port
