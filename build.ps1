$startTime = Get-Date

py -3.8 -m venv venv
.\venv\Scripts\Activate.ps1
python.exe -m pip install --upgrade pip
pip install nuitka==4.1.3

python .\savebuildtime.py

$env:CL = "/utf-8"

nuitka --standalone `
--windows-console-mode=disable `
--enable-plugin=tk-inter `
--windows-company-name="IYATT-yx" `
--windows-product-name="ScanFlow 扫码流水线" `
--windows-file-description="ScanFlow 扫码流水线" `
--windows-product-version="1.0.0.0" `
--windows-file-version="1.0.0.0" `
--copyright="Copyright (C) 2026 IYATT-yx. All Rights Reserved." `
--windows-icon-from-ico=.\icon.ico `
--include-data-file=.\icon.ico=.\ `
--output-dir=dist `
--output-filename=ScanFlow_win_amd64 `
.\ScanFlow.py

$endTime = Get-Date
$elapsedTime = New-TimeSpan -Start $startTime -End $endTime
Write-Output "程序构建用时：$($elapsedTime.TotalSeconds) 秒"