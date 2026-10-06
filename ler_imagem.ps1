param([Parameter(Mandatory=$true)][string]$Caminho)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
function Aguardar($Operacao, [Type]$Tipo) {
    $tarefa = $asTask.MakeGenericMethod($Tipo).Invoke($null, @($Operacao))
    $tarefa.GetAwaiter().GetResult()
}
$motor = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($null -eq $motor) { throw 'O leitor de texto do Windows nao esta disponivel.' }
$arquivo = Aguardar ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Caminho)) ([Windows.Storage.StorageFile])
$fluxo = Aguardar ($arquivo.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
try {
    $decoder = Aguardar ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($fluxo)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Aguardar ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    try {
        $resultado = Aguardar ($motor.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        @{ texto = ($resultado.Lines | ForEach-Object { $_.Text }) -join "`n" } | ConvertTo-Json -Compress
    } finally { $bitmap.Dispose() }
} finally { $fluxo.Dispose() }
