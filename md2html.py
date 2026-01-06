import re
import random
import html
import os
import markdown
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

# ========= SELECCIÓN DE ARCHIVOS =========
def seleccionar_archivos():
	root = tk.Tk()
	root.withdraw()

	messagebox.showinfo("Selector de Archivos", "Selecciona el archivo Markdown de entrada")
	input_md = filedialog.askopenfilename(filetypes=[("Archivos Markdown", "*.md")])
	if not input_md:
		messagebox.showerror("Error", "No seleccionaste el archivo Markdown.")
		exit()

	template_html = "./plantillas/plantilla_web.html"

	messagebox.showinfo("Guardar como", "Selecciona la ruta del archivo HTML de salida")
	output_html = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("Archivo HTML", "*.html")])
	if not output_html:
		messagebox.showerror("Error", "No especificaste archivo de salida.")
		exit()

	return input_md, output_html, template_html

input_md, output_html, template_html = seleccionar_archivos()

# ========= FUNCIONES DE PROTECCIÓN LATEX =========
# Esta función evita que el renderizador de Markdown rompa las fórmulas
def procesar_con_latex(texto):
	# Almacén temporal para las fórmulas
	mapa_latex = {}
	def escudar(match):
		placeholder = f"LATEX_PLACEHOLDER_{len(mapa_latex)}_"
		mapa_latex[placeholder] = match.group(0)
		return placeholder

	# Detectar tanto $$ ... $$ como $ ... $
	# La regex busca primero los bloques de doble $$ para no romperlos
	texto_protegido = re.sub(r'(\$\$.*?\$\$|\$.*?\$)', escudar, texto, flags=re.DOTALL)
	
	# Convertir el resto a Markdown
	html_renderizado = markdown.markdown(texto_protegido, extensions=['extra', 'tables', 'fenced_code'])
	
	# Restaurar las fórmulas originales
	for placeholder, original in mapa_latex.items():
		html_renderizado = html_renderizado.replace(placeholder, original)
	
	return html_renderizado

# ========= VALIDACIÓN Y LECTURA =========
if not os.path.isfile(input_md):
	print(f"El archivo '{input_md}' no existe.")
	exit(1)

with open(input_md, 'r', encoding='utf-8') as f:
	md_content = f.read()

# ========= METADATOS =========
titulo_match = re.search(r'^#\s*(.+)', md_content, flags=re.MULTILINE)
TITULO_TEST = titulo_match.group(1).strip() if titulo_match else 'Test Genérico'

# ========= PARSEO PREGUNTAS =========
pattern = re.compile(
	r'(?m)^(\d+)(\*?)\.\s+(.*?)\n(?=(?:-?\s*\((?:x|\s|\(\))\)))',
	re.DOTALL
)
option_pattern = re.compile(r'-\s*\((x|\s|\(\))\)\s*(.*?)(?=\n\s*-\s*\(|\n\d+\.|\Z|\n\s*#)', re.DOTALL)

questions_data = []
matches = list(pattern.finditer(md_content))

for i, match in enumerate(matches):
	question_number, asterisco, question_text = match.groups()    
	es_multirespuesta = (asterisco == '*')

	start_pos = match.end()
	end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(md_content)
	question_block = md_content[start_pos:end_pos]

	explanation_text = ""
	expl_match = re.search(r'(?m)^#\s*(.*)', question_block)
	if expl_match:
		explanation_text = expl_match.group(1).strip()

	opciones = []
	for o in option_pattern.finditer(question_block):
		opciones.append((o.group(1).strip(), o.group(2).strip()))

	correct_indexes = [idx for idx, (mark, _) in enumerate(opciones) if mark == 'x']

	questions_data.append({
		'question_raw': question_text.strip(),
		'options_raw': opciones,
		'correct': correct_indexes,
		'is_multi': es_multirespuesta,
		'explanation': explanation_text
	})

random.shuffle(questions_data)

# ========= GENERAR HTML =========
html_questions = ''
for idx, q in enumerate(questions_data, 1):
	input_type = "checkbox" if q['is_multi'] else "radio"
	
	# Usamos la nueva función para el enunciado
	question_html = procesar_con_latex(q['question_raw'])
	if question_html.strip().startswith('<p>') and question_html.strip().endswith('</p>'):
		question_html = question_html.strip()[3:-4]

	html_questions += (
		f'<div class="question" id="q{idx}" data-correct="{",".join(str(i) for i in q["correct"])}">\n'
		f'<div class="enunciado"><strong>{idx}.</strong> {question_html}</div>\n<ol type="a">\n'
	)

	for opt_idx, (_, opt_text) in enumerate(q['options_raw']):
		# Usamos la nueva función para cada opción
		opt_html = procesar_con_latex(opt_text)
		if opt_html.strip().startswith('<p>') and opt_html.strip().endswith('</p>'):
			opt_html = opt_html.strip()[3:-4]
			
		html_questions += (
			f'<li><label class="opcion-linea"><input type="{input_type}" name="q{idx}" value="{opt_idx}"> '
			f'<span>{opt_html}</span></label></li>\n'
		)
	
	html_questions += '</ol>\n'
	
	if q['explanation']:
		expl_html = procesar_con_latex(f"**Justificación:** {q['explanation']}")
		html_questions += f'<div class="explicacion" style="display:none; margin-top:15px; padding:15px; border-left:4px solid #3b82f6; background: rgba(255,255,255,0.05); border-radius: 0 10px 10px 0;">{expl_html}</div>\n'
	
	html_questions += '</div>\n'

# ========= REEMPLAZO Y GUARDADO =========
if os.path.isfile(template_html):
	with open(template_html, 'r', encoding='utf-8') as f:
		html_template = f.read()

	final_html = html_template\
		.replace('{{TITULO}}', html.escape(TITULO_TEST))\
		.replace('{{PREGUNTAS_HTML}}', html_questions)

	with open(output_html, 'w', encoding='utf-8') as f:
		f.write(final_html)
	print(f"\n¡Éxito! Test guardado en: {output_html}")
else:
	print(f"Error: No se encontró la plantilla en {template_html}")