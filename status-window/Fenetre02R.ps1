# Fenetre d'etat de la Yamaha 02R pour Ableton Live
# Recoit l'etat envoye par le Remote Script Yamaha02R (UDP 127.0.0.1:9002)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class W32 {
    [DllImport("user32.dll")] public static extern bool ReleaseCapture();
    [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, int msg, int wp, int lp);
}
"@

$PORT = 9002
$N = 16
$W = 74
$H = 92
$cellBg = [System.Drawing.Color]::FromArgb(45, 45, 45)
$cellSel = [System.Drawing.Color]::FromArgb(70, 70, 95)

$form = New-Object System.Windows.Forms.Form
$form.Text = "Yamaha 02R - Etat"
$form.TopMost = $true
$form.BackColor = [System.Drawing.Color]::FromArgb(28, 28, 28)
$form.FormBorderStyle = 'None'
$form.ShowInTaskbar = $true
$form.MinimumSize = New-Object System.Drawing.Size(400, 64)
$HEAD = 30
$form.StartPosition = 'Manual'
$form.Location = New-Object System.Drawing.Point(20, 20)
$form.ClientSize = New-Object System.Drawing.Size(($N * $W + 16), ($H + 66))

# Taille et position memorisees d'une fois sur l'autre
$cfg = Join-Path $PSScriptRoot "Fenetre02R.cfg"
if (Test-Path $cfg) {
    try {
        $v = (Get-Content $cfg -Raw).Trim() -split ","
        $form.Location = New-Object System.Drawing.Point([int]$v[0], [int]$v[1])
        $form.Size = New-Object System.Drawing.Size([int]$v[2], [int]$v[3])
    } catch { }
}

$title = New-Object System.Windows.Forms.Label
$title.ForeColor = [System.Drawing.Color]::White
$title.Font = New-Object System.Drawing.Font('Segoe UI', 13, [System.Drawing.FontStyle]::Bold)
$title.Location = New-Object System.Drawing.Point(8, 3)
$title.AutoSize = $true
$title.Text = "En attente d'Ableton..."
$form.Controls.Add($title)

$info = New-Object System.Windows.Forms.Label
$info.ForeColor = [System.Drawing.Color]::Silver
$info.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$info.Location = New-Object System.Drawing.Point(300, 9)
$info.AutoSize = $true
$info.Text = ""
$form.Controls.Add($info)

# Sans barre de titre : on deplace la fenetre en cliquant-glissant sur la zone du haut
$drag = {
    param($sender, $e)
    if ($e.Button -eq [System.Windows.Forms.MouseButtons]::Left) {
        [W32]::ReleaseCapture() | Out-Null
        [W32]::SendMessage($form.Handle, 0xA1, 2, 0) | Out-Null
    }
}
$form.Add_MouseDown($drag)
$title.Add_MouseDown($drag)
$info.Add_MouseDown($drag)

# Croix de fermeture en haut a droite
$close = New-Object System.Windows.Forms.Label
$close.Text = [char]0x2715
$close.ForeColor = [System.Drawing.Color]::Gray
$close.Font = New-Object System.Drawing.Font('Segoe UI', 11)
$close.Size = New-Object System.Drawing.Size(26, 24)
$close.TextAlign = 'MiddleCenter'
$close.Location = New-Object System.Drawing.Point(($form.ClientSize.Width - 28), 2)
$close.Anchor = 'Top, Right'
$close.Cursor = [System.Windows.Forms.Cursors]::Hand
$close.Add_MouseEnter({ $close.ForeColor = [System.Drawing.Color]::Tomato })
$close.Add_MouseLeave({ $close.ForeColor = [System.Drawing.Color]::Gray })
$close.Add_Click({ $form.Close() })
$form.Controls.Add($close)

# Poignee de redimensionnement en bas a droite
$grip = New-Object System.Windows.Forms.Label
$grip.Text = [char]0x25E2
$grip.ForeColor = [System.Drawing.Color]::DimGray
$grip.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$grip.Size = New-Object System.Drawing.Size(16, 16)
$grip.TextAlign = 'BottomRight'
$grip.Location = New-Object System.Drawing.Point(($form.ClientSize.Width - 16), ($form.ClientSize.Height - 16))
$grip.Anchor = 'Bottom, Right'
$grip.Cursor = [System.Windows.Forms.Cursors]::SizeNWSE
$grip.Add_MouseDown({
    param($sender, $e)
    if ($e.Button -eq [System.Windows.Forms.MouseButtons]::Left) {
        [W32]::ReleaseCapture() | Out-Null
        [W32]::SendMessage($form.Handle, 0xA1, 17, 0) | Out-Null
    }
})
$form.Controls.Add($grip)

# Couleurs et etiquettes des gommettes (memes que sur la console)
$cW='#F1EFE8'; $cBR='#7A4A24'; $cBL='#378ADD'; $cGR='#639922'; $cRD='#E24B4A'
$cYE='#F2C230'; $cOR='#F0801F'; $cVI='#7F77DD'; $cPK='#ED93B1'; $cGY='#888780'
$eqColors = @($cW,$cW,$cBR,$cBR,$cBL,$cBL,$cBL,$cGR,$cGR,$cGR,$cRD,$cRD,$cYE,$cOR,$cOR,$cOR)
$eqLabels = @('HPF','LPF','LF Fréq','LF dB','LMF Q','LMF Fréq','LMF dB','HMF Q','HMF Fréq','HMF dB','HF Fréq','HF dB','OUT','Comp Thr','Comp Ratio','Comp Mix')
$rvColors = @($cVI,$cVI,$cVI,$cVI,$cPK,$cPK,$cPK,$cPK,$cW,$cW,$cBR,$cRD,$cOR,$cYE,$cYE,$cGY)
$rvLabels = @('Pré-délai','Temps','Early','Tail','Mult Grave','Mult Aigu','X-ov Grave','X-ov Aigu','HPF','LPF','Low dB','High dB','Comp Thr','OUT','IN','Kill')

$cells = @()
for ($i = 0; $i -lt $N; $i++) {
    $p = New-Object System.Windows.Forms.Panel
    $p.Location = New-Object System.Drawing.Point((8 + $i * $W), 60)
    $p.Size = New-Object System.Drawing.Size(($W - 4), $H)
    $p.BackColor = $cellBg

    $bar = New-Object System.Windows.Forms.Panel
    $bar.Location = New-Object System.Drawing.Point(0, 0)
    $bar.Size = New-Object System.Drawing.Size(($W - 4), 6)
    $bar.BackColor = [System.Drawing.Color]::DimGray
    $p.Controls.Add($bar)

    $num = New-Object System.Windows.Forms.Label
    $num.ForeColor = [System.Drawing.Color]::Gray
    $num.Font = New-Object System.Drawing.Font('Segoe UI', 8)
    $num.Location = New-Object System.Drawing.Point(3, 9)
    $num.Size = New-Object System.Drawing.Size(($W - 8), 15)
    $num.Text = "" + ($i + 1)
    $p.Controls.Add($num)

    $name = New-Object System.Windows.Forms.Label
    $name.ForeColor = [System.Drawing.Color]::White
    $name.Font = New-Object System.Drawing.Font('Segoe UI', 9, [System.Drawing.FontStyle]::Bold)
    $name.Location = New-Object System.Drawing.Point(3, 26)
    $name.Size = New-Object System.Drawing.Size(($W - 8), 42)
    $p.Controls.Add($name)

    $st = New-Object System.Windows.Forms.Label
    $st.Font = New-Object System.Drawing.Font('Segoe UI', 8, [System.Drawing.FontStyle]::Bold)
    $st.Location = New-Object System.Drawing.Point(3, 70)
    $st.Size = New-Object System.Drawing.Size(($W - 8), 16)
    $p.Controls.Add($st)

    $form.Controls.Add($p)
    $cells += , @($p, $bar, $num, $name, $st)
}

# Cases des potards (modes EQ, Retour, Plugin)
$kcells = @()
for ($i = 0; $i -lt $N; $i++) {
    $p = New-Object System.Windows.Forms.Panel
    $p.BackColor = $cellBg
    $p.Visible = $false
    $dot = New-Object System.Windows.Forms.Panel
    $dot.BackColor = [System.Drawing.Color]::DimGray
    $p.Controls.Add($dot)
    $lbl = New-Object System.Windows.Forms.Label
    $lbl.ForeColor = [System.Drawing.Color]::White
    $lbl.TextAlign = 'MiddleCenter'
    $p.Controls.Add($lbl)
    $pn = New-Object System.Windows.Forms.Label
    $pn.ForeColor = [System.Drawing.Color]::Gray
    $pn.TextAlign = 'TopCenter'
    $p.Controls.Add($pn)
    $val = New-Object System.Windows.Forms.Label
    $val.ForeColor = [System.Drawing.Color]::White
    $val.TextAlign = 'MiddleCenter'
    $p.Controls.Add($val)
    $bg = New-Object System.Windows.Forms.Panel
    $bg.BackColor = [System.Drawing.Color]::FromArgb(25, 25, 25)
    $fill = New-Object System.Windows.Forms.Panel
    $fill.Location = New-Object System.Drawing.Point(0, 0)
    $fill.Width = 0
    $bg.Controls.Add($fill)
    $p.Controls.Add($bg)
    $form.Controls.Add($p)
    $kcells += , @($p, $dot, $lbl, $pn, $val, $bg, $fill)
}
$script:norms = @(0.0) * $N

# Recalcule la place de chaque case quand on redimensionne la fenetre
function Get-Font($size, $bold) {
    $size = [Math]::Max(6.5, $size)
    if ($bold) { return New-Object System.Drawing.Font('Segoe UI', $size, [System.Drawing.FontStyle]::Bold) }
    return New-Object System.Drawing.Font('Segoe UI', $size)
}
$script:compact = $false

function Layout-Cells {
    $cw = [Math]::Max(24, [int](($form.ClientSize.Width - 16) / $N))
    $ch = [Math]::Max(26, $form.ClientSize.Height - $HEAD - 6)
    $k = [Math]::Min(2.5, [Math]::Max(0.5, [Math]::Min($cw / $W, $ch / $H)))
    $small = ($ch -lt 60)
    $fNum = Get-Font (8 * $k) $false
    $fName = Get-Font (9 * [Math]::Max($k, 0.85)) $true
    $fSt = Get-Font (8 * [Math]::Max($k, 0.85)) $true
    for ($i = 0; $i -lt $N; $i++) {
        $c = $cells[$i]
        $c[0].Location = New-Object System.Drawing.Point((8 + $i * $cw), $HEAD)
        $c[0].Size = New-Object System.Drawing.Size(($cw - 4), $ch)
        $c[1].Size = New-Object System.Drawing.Size(($cw - 4), [Math]::Max(3, [int](6 * $k)))
        $c[2].Visible = -not $small
        $c[2].Font = $fNum
        $c[2].Location = New-Object System.Drawing.Point(3, [int](9 * $k))
        $c[2].Size = New-Object System.Drawing.Size(($cw - 8), [int](15 * $k))
        $c[3].Font = $fName
        $stH = [int]($fSt.Height + 2)
        if ($small) {
            $c[3].Location = New-Object System.Drawing.Point(3, ($c[1].Height + 3))
            $c[3].Size = New-Object System.Drawing.Size(($cw - 8), [Math]::Max(10, $ch - $c[1].Height - $stH - 3))
        } else {
            $c[3].Location = New-Object System.Drawing.Point(3, [int](26 * $k))
            $c[3].Size = New-Object System.Drawing.Size(($cw - 8), [Math]::Max(10, $ch - [int](26 * $k) - $stH - 4))
        }
        $c[4].Font = $fSt
        $c[4].Location = New-Object System.Drawing.Point(3, ($ch - $stH - 1))
        $c[4].Size = New-Object System.Drawing.Size(($cw - 8), $stH)
    }
}

function Layout-Knobs {
    $cw = [Math]::Max(24, [int](($form.ClientSize.Width - 16) / $N))
    $ch = [Math]::Max(26, $form.ClientSize.Height - $HEAD - 6)
    $k = [Math]::Min(2.5, [Math]::Max(0.5, [Math]::Min($cw / $W, $ch / $H)))
    $script:compact = ($ch -lt 80)
    $fLbl = Get-Font (8.5 * [Math]::Max($k, 0.85)) $true
    $fPn = Get-Font (7 * $k) $false
    $fVal = Get-Font (9 * [Math]::Max($k, 0.85)) $true
    $d = [Math]::Max(8, [int](14 * $k))
    $barH = [Math]::Max(3, [int](6 * $k))
    $valH = [int]($fVal.Height + 1)
    $lblH = [int]($fLbl.Height + 1)
    for ($i = 0; $i -lt $N; $i++) {
        $c = $kcells[$i]
        $c[0].Location = New-Object System.Drawing.Point((8 + $i * $cw), $HEAD)
        $c[0].Size = New-Object System.Drawing.Size(($cw - 4), $ch)
        $c[1].Visible = -not $script:compact
        $c[3].Visible = -not $script:compact
        $c[1].Location = New-Object System.Drawing.Point([int](($cw - 4 - $d) / 2), [int](5 * $k))
        $c[1].Size = New-Object System.Drawing.Size($d, $d)
        $gp = New-Object System.Drawing.Drawing2D.GraphicsPath
        $gp.AddEllipse(0, 0, $d, $d)
        $c[1].Region = New-Object System.Drawing.Region($gp)
        $c[2].Font = $fLbl
        if ($script:compact) {
            $c[2].Location = New-Object System.Drawing.Point(1, 2)
        } else {
            $c[2].Location = New-Object System.Drawing.Point(1, ([int](5 * $k) + $d + 2))
        }
        $c[2].Size = New-Object System.Drawing.Size(($cw - 6), $lblH)
        $c[3].Font = $fPn
        $c[3].Location = New-Object System.Drawing.Point(1, ($c[2].Bottom + 1))
        $c[3].Size = New-Object System.Drawing.Size(($cw - 6), [Math]::Max(10, $ch - $c[2].Bottom - $valH - $barH - 8))
        $c[4].Font = $fVal
        $c[4].Location = New-Object System.Drawing.Point(1, ($ch - $valH - $barH - 4))
        $c[4].Size = New-Object System.Drawing.Size(($cw - 6), $valH)
        $c[5].Location = New-Object System.Drawing.Point(4, ($ch - $barH - 3))
        $c[5].Size = New-Object System.Drawing.Size(($cw - 12), $barH)
        $c[6].Height = $barH
        $c[6].Width = [int]($script:norms[$i] * $c[5].Width)
        if ($script:compact) { $c[2].ForeColor = $c[1].BackColor } else { $c[2].ForeColor = [System.Drawing.Color]::White }
    }
}
Layout-Cells
Layout-Knobs
$close.BringToFront()
$grip.BringToFront()
$form.Add_Resize({ Layout-Cells; Layout-Knobs })

function Update-View($s) {
    $title.Text = "Pistes $($s.first)-$($s.last)    |    Potards : $($s.mode)"
    $info.Left = $title.Right + 24
    $parts = @()
    if ($s.shift) { $parts += "SHIFT" }
    if ($s.follow) { $parts += "Suivi : ON" } else { $parts += "Suivi : OFF" }
    if ($s.alert) { $parts += ("ATTENTION voyants ON decales : " + $s.alert) }
    $info.Text = $parts -join "    |    "
    if ($s.alert) { $info.ForeColor = [System.Drawing.Color]::Orange }
    elseif ($s.shift) { $info.ForeColor = [System.Drawing.Color]::Gold }
    else { $info.ForeColor = [System.Drawing.Color]::Silver }

    $showKnobs = ($s.view -eq 'knobs')
    for ($i = 0; $i -lt $N; $i++) {
        $cells[$i][0].Visible = -not $showKnobs
        $kcells[$i][0].Visible = $showKnobs
    }
    if ($showKnobs) {
        $colors = $null; $labels = $null
        if ($s.page -eq 0 -and $s.modeidx -eq 4) { $colors = $eqColors; $labels = $eqLabels }
        elseif ($s.page -eq 0 -and $s.modeidx -eq 5) { $colors = $rvColors; $labels = $rvLabels }
        for ($i = 0; $i -lt $N; $i++) {
            $c = $kcells[$i]
            $kn = $s.knobs[$i]
            if ($kn -and $kn.name) {
                if ($colors) {
                    $c[1].BackColor = [System.Drawing.ColorTranslator]::FromHtml($colors[$i])
                    $c[2].Text = $labels[$i]
                    $c[3].Text = $kn.name
                } else {
                    $c[1].BackColor = [System.Drawing.Color]::DimGray
                    $c[2].Text = "" + ($i + 1)
                    $c[3].Text = $kn.name
                }
                $c[6].BackColor = $c[1].BackColor
                if ($script:compact) { $c[2].ForeColor = $c[1].BackColor } else { $c[2].ForeColor = [System.Drawing.Color]::White }
                $c[4].Text = $kn.value
                $script:norms[$i] = [double]$kn.norm
            } else {
                $c[1].BackColor = [System.Drawing.Color]::FromArgb(35, 35, 35)
                $c[2].Text = "" + ($i + 1)
                $c[3].Text = ""
                $c[4].Text = "-"
                $script:norms[$i] = 0.0
            }
            $c[6].Width = [int]($script:norms[$i] * $c[5].Width)
        }
        return
    }
    for ($i = 0; $i -lt $N; $i++) {
        $c = $cells[$i]
        $t = $s.strips[$i]
        $c[2].Text = "" + $t.num
        if ($t.name) {
            $c[3].Text = $t.name
            try { $c[1].BackColor = [System.Drawing.ColorTranslator]::FromHtml($t.color) } catch { }
            $flags = @()
            if ($t.mute) { $flags += "MUTE" }
            if ($t.arm) { $flags += "REC" }
            $c[4].Text = $flags -join " "
            if ($t.arm) { $c[4].ForeColor = [System.Drawing.Color]::Tomato }
            else { $c[4].ForeColor = [System.Drawing.Color]::Orange }
            if ($t.mute) { $c[3].ForeColor = [System.Drawing.Color]::Gray }
            else { $c[3].ForeColor = [System.Drawing.Color]::White }
            if ($t.sel) { $c[0].BackColor = $cellSel } else { $c[0].BackColor = $cellBg }
        }
        else {
            $c[3].Text = ""
            $c[4].Text = ""
            $c[1].BackColor = [System.Drawing.Color]::FromArgb(35, 35, 35)
            $c[0].BackColor = $cellBg
        }
    }
}

try {
    $ep = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Loopback, $PORT)
    $udp = New-Object System.Net.Sockets.UdpClient($ep)
}
catch {
    [System.Windows.Forms.MessageBox]::Show("Le port $PORT est deja utilise. La fenetre est peut-etre deja ouverte.", "Yamaha 02R") | Out-Null
    exit
}

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 100
$timer.Add_Tick({
    $last = $null
    $remote = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any, 0)
    while ($udp.Available -gt 0) {
        $bytes = $udp.Receive([ref]$remote)
        $last = [System.Text.Encoding]::UTF8.GetString($bytes)
    }
    if ($last) {
        try { Update-View ($last | ConvertFrom-Json) } catch { }
    }
})
$timer.Start()

$form.Add_FormClosing({
    try {
        if ($form.WindowState -eq 'Normal') {
            "$($form.Left),$($form.Top),$($form.Width),$($form.Height)" | Set-Content $cfg
        }
    } catch { }
})
$form.Add_FormClosed({ $timer.Stop(); $udp.Close() })
[System.Windows.Forms.Application]::Run($form)
