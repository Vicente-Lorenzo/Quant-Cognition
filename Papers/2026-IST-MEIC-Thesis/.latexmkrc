# Build and live preview of the dissertation
# latexmk -pvc Main.tex rebuilds on every save; SumatraPDF reloads the PDF itself
$pdf_mode = 1;
$pdflatex = 'pdflatex -interaction=nonstopmode -file-line-error -synctex=1 %O %S';
$pdf_previewer = '"" "C:/Users/Admin/AppData/Local/SumatraPDF/SumatraPDF.exe" -reuse-instance %O %S';
$pdf_update_method = 0;
