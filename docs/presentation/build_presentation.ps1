$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$items = Get-Content (Join-Path $PSScriptRoot 'deck_content.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$renderDir = Join-Path $root 'docs/evidence/capstone/rendered'
New-Item -ItemType Directory -Path $renderDir -Force | Out-Null
$shotDir = Join-Path $root 'docs/evidence/capstone/screenshots'
function RGB([string]$hex) { return [Convert]::ToInt32($hex.Substring(0,2),16) + 256*[Convert]::ToInt32($hex.Substring(2,2),16) + 65536*[Convert]::ToInt32($hex.Substring(4,2),16) }
$plum=RGB '5B2453'; $mint=RGB '67C9C5'; $paper=RGB 'F7F7F5'; $ink=RGB '30263B'; $muted=RGB '6C6570'; $white=RGB 'FFFFFF'; $soft=RGB 'E8F5F3'
$script:issues = [System.Collections.Generic.List[object]]::new()
$script:allText = [System.Collections.Generic.List[object]]::new()
function Rect($slide,$x,$y,$w,$h,$color,$rounded=$false) {
 $shape=$slide.Shapes.AddShape($(if($rounded){5}else{1}),$x,$y,$w,$h)
 $shape.Fill.ForeColor.RGB=$color; $shape.Line.Visible=0
 return $shape
}
function Txt($slide,$value,$x,$y,$w,$h,$size=18,$color=$ink,$bold=$false,$align=3,$rtl=$true) {
 $box=$slide.Shapes.AddTextbox(1,$x,$y,$w,$h)
 $tf=$box.TextFrame; $tf.MarginLeft=3; $tf.MarginRight=3; $tf.MarginTop=2; $tf.MarginBottom=2; $tf.WordWrap=-1
 $tr=$tf.TextRange; $tr.Text=[string]$value; $tr.Font.Name='Arial'; $tr.Font.Size=$size; $tr.Font.Color.RGB=$color; $tr.Font.Bold=$(if($bold){-1}else{0})
 $tr.Font.NameComplexScript='Arial'
 $tr.ParagraphFormat.TextDirection=$(if($rtl){2}else{1}); $tr.ParagraphFormat.Alignment=$align; $tr.ParagraphFormat.SpaceAfter=4
 $actual=$size
 while ($tr.BoundHeight -gt ($h-4) -and $actual -gt 14) { $actual=[double]$actual-0.5; $tr.Font.Size=[single]$actual }
 if($tr.BoundHeight -gt ($h-3)) { $script:issues.Add([pscustomobject]@{slide=$slide.SlideIndex;text=([string]$value).Substring(0,[Math]::Min(90,([string]$value).Length));height=$h;bound=$tr.BoundHeight}) }
 $script:allText.Add([pscustomobject]@{slide=$slide.SlideIndex;font=$actual;characters=([string]$value).Length;type=$(if($size -le 11){'reference'}else{'content'})})
 return $box
}
function Cards($slide,$cards,$y,$height) {
 $count=@($cards).Count; if($count -eq 0){return}
 $gap=14; $cw=(876-($count-1)*$gap)/$count
 for($j=0;$j -lt $count;$j++) {
  $x=42+($count-1-$j)*($cw+$gap)
  $null=Rect $slide $x $y $cw $height $white $true
  if($height -lt 125) {
   $null=Txt $slide ($cards[$j].title+': '+$cards[$j].text) ($x+13) ($y+8) ($cw-26) ($height-16) 17
   continue
  }
  $null=Rect $slide ($x+$cw-7) ($y+16) 4 28 $mint
  $null=Txt $slide $cards[$j].title ($x+13) ($y+12) ($cw-28) 49 20 $plum $true
  $null=Txt $slide $cards[$j].text ($x+13) ($y+66) ($cw-26) ($height-77) 19
 }
}
function Table($slide,$data,$y,$height,$font=18,$width=876,$left=42) {
 $cols=@($data.headers).Count; $rows=@($data.rows).Count; $cw=$width/$cols; $hh=37; $rh=($height-$hh)/$rows
 for($c=0;$c -lt $cols;$c++) {
  $x=$left+($cols-1-$c)*$cw
  $null=Rect $slide $x $y ($cw-2) $hh $plum
  $null=Txt $slide $data.headers[$c] ($x+6) ($y+4) ($cw-14) ($hh-6) 16 $white $true
  for($r=0;$r -lt $rows;$r++) {
   $yy=$y+$hh+$r*$rh
   $bg=$(if($r%2 -eq 0){$white}else{$soft})
   $null=Rect $slide $x $yy ($cw-2) ($rh-2) $bg
   $null=Txt $slide $data.rows[$r][$c] ($x+7) ($yy+3) ($cw-16) ($rh-6) $font $ink ($c -eq 0)
  }
 }
}
$hadPowerPoint = @(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app=New-Object -ComObject PowerPoint.Application
$deck=$null
try {
 $deck=$app.Presentations.Add(0); $deck.PageSetup.SlideWidth=960; $deck.PageSetup.SlideHeight=540
 for($i=0;$i -lt $items.Count;$i++) {
  $d=$items[$i]; $s=$deck.Slides.Add($i+1,12); $s.FollowMasterBackground=0; $s.Background.Fill.ForeColor.RGB=$paper
  $null=Rect $s 0 0 960 8 $plum
  $null=Txt $s 'MEETSPACE / SDAIA CAPSTONE' 42 16 550 22 10 $muted $false 1 $false
  $null=Txt $s ('{0:D2} / {1:D2}' -f ($i+1),$items.Count) 812 16 106 22 10 $muted $false 3 $false
  $null=Txt $s $d.title 42 46 876 54 30 $plum $true
  $null=Txt $s $d.intro 42 104 876 63 19 $ink
  if($d.kind -eq 'images') {
   $n=@($d.images).Count; $cw=(876-18)/2
   for($k=0;$k -lt $n;$k++) {
    $x=42+$k*($cw+18); $path=Join-Path $shotDir $d.images[$k].file
    $null=Rect $s $x 174 $cw 303 $white $true
    $pic=$s.Shapes.AddPicture($path,0,-1,0,0,-1,-1)
    $scale=[Math]::Min(($cw-14)/$pic.Width,265/$pic.Height)
    $pic.LockAspectRatio=-1; $pic.Width=$pic.Width*$scale
    $pic.Left=$x+($cw-$pic.Width)/2; $pic.Top=180+(265-$pic.Height)/2
    $null=Txt $s $d.images[$k].caption ($x+6) 448 ($cw-12) 25 14 $plum $true
   }
  } elseif($d.kind -eq 'chart') {
   Table $s $d.table 178 272 18 495 423
   $null=Txt $s 'Elapsed seconds / actual reported data' 42 179 365 30 13 $muted $false 1 $false
   $manual=@(158,221,358); $tool=@(58,66,106); $names=@('Typical','Messy','Edge')
   for($j=0;$j -lt 3;$j++) {
    $yy=219+$j*76
    $null=Txt $s $names[$j] 42 $yy 75 21 14 $ink $true 1 $false
    $null=Rect $s 123 $yy ($manual[$j]*0.62) 18 $plum
    $null=Rect $s 123 ($yy+25) ($tool[$j]*0.62) 18 $mint
    $null=Txt $s ([string]$manual[$j]) (128+$manual[$j]*0.62) ($yy-1) 45 23 13 $plum $true 1 $false
    $null=Txt $s ([string]$tool[$j]) (128+$tool[$j]*0.62) ($yy+24) 45 23 13 $ink $true 1 $false
   }
   $null=Txt $s 'Plum: Email + Excel | Mint: MeetSpace' 42 453 365 23 12 $muted $false 1 $false
   $null=Txt $s '68.79% observed total time reduction' 423 455 495 28 19 $plum $true 2 $false
  } elseif($null -ne $d.table) {
   if(@($d.cards).Count -gt 0) { Table $s $d.table 178 215 18; Cards $s $d.cards 404 81 }
   else { Table $s $d.table 178 305 19 }
  } else {
   Cards $s $d.cards 184 300
  }
  $null=Rect $s 42 493 876 1 $mint
  if($i -eq 25) {
   $null=Txt $s $d.source 42 494 876 45 9 $muted $false 1 $false
  } else { $null=Txt $s $d.source 42 499 876 35 10 $muted }
  Write-Output ('Created slide '+($i+1))
 }
 $pptx=Join-Path $root 'MeetSpace_Final_Presentation.pptx'; $pdf=Join-Path $root 'MeetSpace_Final_Presentation.pdf'
 $deck.SaveAs($pptx,24); $deck.SaveAs($pdf,32)
 foreach($s in $deck.Slides) { $s.Export((Join-Path $renderDir ('slide_{0:D2}.png' -f $s.SlideIndex)),'PNG',1600,900) }
 [pscustomobject]@{slides=$deck.Slides.Count;overflow=@($script:issues);text=@($script:allText);generated_at=(Get-Date).ToString('o');pptx=$pptx;pdf=$pdf} | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $root 'docs/evidence/capstone/layout_check.json') -Encoding UTF8
 Write-Output ('Saved '+$pptx); Write-Output ('Saved '+$pdf); Write-Output ('Overflow issues: '+$script:issues.Count)
} finally {
 if($null -ne $deck){$deck.Close()}; if(-not $hadPowerPoint){$app.Quit()}
}
