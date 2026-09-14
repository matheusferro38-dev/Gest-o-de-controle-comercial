import csv
import hashlib
import json
import os
import socket
import shutil
import sqlite3
import tkinter as tk
import webbrowser
import zipfile
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk
from urllib.parse import quote
from xml.sax.saxutils import escape
from api_server import NexaStockApi

PASTA_SISTEMA = os.path.dirname(os.path.abspath(__file__))
PASTA_IMAGENS = os.path.join(PASTA_SISTEMA, "imagens")
ARQUIVO_BANCO_ANTIGO = os.path.join(PASTA_SISTEMA, "churrascaria.db")
ARQUIVO_BANCO = os.path.join(PASTA_SISTEMA, "Banco de dados.db")
ARQUIVO_ESTOQUE = os.path.join(PASTA_SISTEMA, "estoque.db")
ARQUIVO_VENDAS = os.path.join(PASTA_SISTEMA, "vendas.db")
ARQUIVO_PEDIDOS = os.path.join(PASTA_SISTEMA, "pedidos.db")
PASTA_BACKUPS = os.path.join(os.path.dirname(ARQUIVO_BANCO), "backups")
NOME_SISTEMA = "NEXA"
DESCRICAO_SISTEMA = "Sistema integrado de gestão do estabelecimento"

PALETA = {
	"primaria": "#2F6FED",
	"primaria_escura": "#2458C5",
	"fundo": "#F4F7FB",
	"superficie": "#FFFFFF",
	"texto": "#0F172A",
	"muted": "#64748B",
	"borda": "#E2E8F0",
	"sucesso": "#16A34A",
	"alerta": "#F59E0B",
	"sidebar": "#101827",
	"sidebar_hover": "#1D2A40",
	"sidebar_muted": "#8FA0B8",
}

PALETA_ESCURA = {
	"fundo": "#0B1220",
	"superficie": "#111C2E",
	"texto": "#F1F5F9",
	"muted": "#9AAAC0",
	"borda": "#26364D",
	"sidebar": "#070D18",
	"sidebar_hover": "#17253A",
	"sidebar_muted": "#93A4BC",
}


def aplicar_acabamento_3d(container):
	for widget in container.winfo_children():
		if isinstance(widget, tk.Button):
			widget.configure(relief="raised", bd=1, overrelief="sunken", highlightthickness=0,
							 cursor="hand2")
			aplicar_acabamento_3d(widget)


def configurar_icone_carrinho(janela):
	icone = tk.PhotoImage(width=32, height=32)
	icone.put("#1f2d35", to=(0, 0, 31, 31))
	icone.put("#e8b45b", to=(5, 6, 8, 8))
	icone.put("#e8b45b", to=(8, 8, 25, 10))
	icone.put("#d45b45", to=(10, 11, 25, 19))
	icone.put("#d45b45", to=(12, 19, 23, 21))
	icone.put("#eef3f2", to=(13, 23, 16, 26))
	icone.put("#eef3f2", to=(21, 23, 24, 26))
	janela.iconphoto(True, icone)
	janela._icone_carrinho = icone


def rolar_tabela(evento):
	if evento.num == 4 or evento.delta > 0:
		direcao = -3
	else:
		direcao = 3
	evento.widget.yview_scroll(direcao, "units")
	return "break"


def desenhar_icone_cartao(canvas, tipo, cor):
	canvas.delete("all")
	canvas.configure(width=142, height=92, bg=cor)
	if tipo == "estoque":
		canvas.create_rectangle(35, 34, 105, 74, outline="white", width=3, tags="animado")
		canvas.create_line(35, 34, 70, 50, 105, 34, fill="white", width=3, tags="animado")
		canvas.create_line(70, 50, 70, 74, fill="white", width=3, tags="animado")
		canvas.create_line(35, 34, 35, 24, 70, 39, 105, 24, 105, 34, fill="white", width=3, tags="animado")
		canvas.create_line(51, 60, 63, 65, fill="white", width=3, tags="animado")
	elif tipo == "vendas":
		canvas.create_line(22, 27, 34, 27, 42, 66, 101, 66, 113, 37, 37, 37, fill="white", width=3, tags="animado")
		canvas.create_oval(43, 72, 53, 82, outline="white", width=3, tags="animado")
		canvas.create_oval(91, 72, 101, 82, outline="white", width=3, tags="animado")
		canvas.create_rectangle(50, 21, 67, 37, outline="white", width=2, tags="animado")
		canvas.create_rectangle(73, 16, 91, 37, outline="white", width=2, tags="animado")
	else:
		for x in (38, 88):
			canvas.create_oval(x - 16, 30, x + 16, 62, outline="white", width=3, tags="animado")
			canvas.create_line(x - 23, 27, x - 23, 65, fill="white", width=2, tags="animado")
			canvas.create_line(x + 23, 27, x + 23, 65, fill="white", width=2, tags="animado")
		canvas.create_line(55, 46, 71, 46, fill="white", width=3, tags="animado")
		canvas.create_line(62, 39, 62, 53, fill="white", width=3, tags="animado")


class SistemaEstoque:
	def __init__(self, janela, usuario="admin", nivel="administrador"):
		self.janela = janela
		self.usuario_logado = usuario
		self.nivel_acesso = nivel
		self.tema_escuro = False
		self.janela.title(NOME_SISTEMA + " - " + DESCRICAO_SISTEMA)
		configurar_icone_carrinho(self.janela)
		self.janela.geometry("1280x780")
		self.janela.resizable(True, True)
		self.janela.minsize(1080, 680)
		self.janela.configure(bg=PALETA["fundo"])
		self.migrar_nome_banco()
		self.preparar_bancos_separados()
		self.criar_banco()
		self.api = NexaStockApi(PASTA_SISTEMA, ARQUIVO_ESTOQUE, ARQUIVO_VENDAS, ARQUIVO_PEDIDOS)
		self.api.iniciar()
		self.configurar_estilos()
		self.janela.bind_class("Button", "<Enter>", self._botao_entrou, add="+")
		self.janela.bind_class("Button", "<Leave>", self._botao_saiu, add="+")
		self.janela.bind_class("Button", "<FocusIn>", self._botao_focado, add="+")
		self.janela.bind_class("Button", "<FocusOut>", self._botao_desfocado, add="+")
		self.janela.bind_class("Treeview", "<MouseWheel>", rolar_tabela, add="+")
		self.janela.bind_class("Treeview", "<Button-4>", rolar_tabela, add="+")
		self.janela.bind_class("Treeview", "<Button-5>", rolar_tabela, add="+")
		self.janela.protocol("WM_DELETE_WINDOW", self.fechar_sistema)
		self.fazer_backup_automatico()
		self.janela.after(300000, self.agendar_backup_automatico)
		self.criar_tela_premium()
		aplicar_acabamento_3d(self.janela)
		self.atualizar_tela()

	def _botao_entrou(self, evento):
		botao = evento.widget
		botao.configure(relief="sunken", highlightthickness=1, highlightbackground="#f0bf62")

	def _botao_saiu(self, evento):
		botao = evento.widget
		botao.configure(relief="raised", highlightthickness=0)

	def _botao_focado(self, evento):
		evento.widget.configure(highlightthickness=2, highlightbackground="#f0bf62")

	def _botao_desfocado(self, evento):
		evento.widget.configure(highlightthickness=0)

	def conectar(self):
		banco = sqlite3.connect(ARQUIVO_ESTOQUE)
		banco.execute("ATTACH DATABASE ? AS vendas_db", (ARQUIVO_VENDAS,))
		banco.execute("ATTACH DATABASE ? AS pedidos_db", (ARQUIVO_PEDIDOS,))
		banco.row_factory = sqlite3.Row
		return banco

	def migrar_nome_banco(self):
		if not os.path.exists(ARQUIVO_BANCO) and os.path.exists(ARQUIVO_BANCO_ANTIGO):
			shutil.copy2(ARQUIVO_BANCO_ANTIGO, ARQUIVO_BANCO)

	def preparar_bancos_separados(self):
		origem = ARQUIVO_BANCO if os.path.exists(ARQUIVO_BANCO) else None
		if not os.path.exists(ARQUIVO_ESTOQUE):
			if origem:
				shutil.copy2(origem, ARQUIVO_ESTOQUE)
			else:
				sqlite3.connect(ARQUIVO_ESTOQUE).close()
		with sqlite3.connect(ARQUIVO_ESTOQUE) as estoque:
			for caminho, tabelas in (
				(ARQUIVO_VENDAS, ("vendas", "venda_itens")),
				(ARQUIVO_PEDIDOS, ("pedidos_mesa", "pedido_mesa_itens")),
			):
				if os.path.exists(caminho):
					continue
				with sqlite3.connect(caminho) as destino:
					for tabela in tabelas:
						definicao = estoque.execute(
							"SELECT sql FROM main.sqlite_master WHERE type = 'table' AND name = ?", (tabela,)).fetchone()
						if not definicao:
							continue
						destino.execute(definicao[0])
						colunas = [linha[1] for linha in estoque.execute("PRAGMA main.table_info(" + tabela + ")").fetchall()]
						registros = estoque.execute("SELECT * FROM main." + tabela).fetchall()
						if registros:
							marcadores = ",".join("?" for _ in colunas)
							destino.executemany("INSERT INTO " + tabela + " VALUES (" + marcadores + ")", registros)
					estoque.commit()
			for tabela in ("vendas", "venda_itens", "pedidos_mesa", "pedido_mesa_itens"):
				estoque.execute("DROP TABLE IF EXISTS main." + tabela)

	def criar_banco(self):
		with self.conectar() as banco:
			banco.execute("""CREATE TABLE IF NOT EXISTS insumos (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				nome TEXT NOT NULL,
				estabelecimento TEXT NOT NULL DEFAULT 'Churrascaria',
				categoria TEXT NOT NULL,
				unidade TEXT NOT NULL,
				quantidade REAL NOT NULL DEFAULT 0,
				estoque_minimo REAL NOT NULL DEFAULT 1,
				custo REAL NOT NULL DEFAULT 0,
				fornecedor TEXT NOT NULL DEFAULT '',
				atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
				codigo_barras TEXT NOT NULL DEFAULT '',
				origem TEXT NOT NULL DEFAULT 'estoque'
			)""")
			colunas = [linha[1] for linha in banco.execute("PRAGMA table_info(insumos)").fetchall()]
			if "estabelecimento" not in colunas:
				banco.execute("ALTER TABLE insumos ADD COLUMN estabelecimento TEXT NOT NULL DEFAULT 'Churrascaria'")
			if "codigo_barras" not in colunas:
				banco.execute("ALTER TABLE insumos ADD COLUMN codigo_barras TEXT NOT NULL DEFAULT ''")
			if "origem" not in colunas:
				banco.execute("ALTER TABLE insumos ADD COLUMN origem TEXT NOT NULL DEFAULT 'estoque'")
			banco.execute("""CREATE TABLE IF NOT EXISTS movimentacoes (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				insumo_id INTEGER NOT NULL,
				tipo TEXT NOT NULL,
				quantidade REAL NOT NULL,
				data TEXT DEFAULT CURRENT_TIMESTAMP,
				FOREIGN KEY (insumo_id) REFERENCES insumos(id)
			)""")
			banco.execute("""CREATE TABLE IF NOT EXISTS vendas (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				estabelecimento TEXT NOT NULL,
				usuario TEXT NOT NULL,
				total REAL NOT NULL DEFAULT 0,
				status TEXT NOT NULL DEFAULT 'concluida',
				forma_pagamento TEXT NOT NULL DEFAULT 'Dinheiro',
				comprovante TEXT NOT NULL DEFAULT '',
				data TEXT DEFAULT CURRENT_TIMESTAMP
			)""")
			colunas_vendas = [linha[1] for linha in banco.execute("PRAGMA table_info(vendas)").fetchall()]
			if "forma_pagamento" not in colunas_vendas:
				banco.execute("ALTER TABLE vendas ADD COLUMN forma_pagamento TEXT NOT NULL DEFAULT 'Dinheiro'")
			if "comprovante" not in colunas_vendas:
				banco.execute("ALTER TABLE vendas ADD COLUMN comprovante TEXT NOT NULL DEFAULT ''")
			banco.execute("""CREATE TABLE IF NOT EXISTS venda_itens (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				venda_id INTEGER NOT NULL,
				insumo_id INTEGER NOT NULL,
				nome TEXT NOT NULL,
				quantidade REAL NOT NULL,
				preco_unitario REAL NOT NULL,
				subtotal REAL NOT NULL,
				FOREIGN KEY (venda_id) REFERENCES vendas(id),
				FOREIGN KEY (insumo_id) REFERENCES insumos(id)
			)""")
			banco.execute("""CREATE TABLE IF NOT EXISTS pedidos_mesa (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				mesa TEXT NOT NULL,
				estabelecimento TEXT NOT NULL,
				usuario TEXT NOT NULL,
				total REAL NOT NULL DEFAULT 0,
				status TEXT NOT NULL DEFAULT 'aberto',
				aberto_em TEXT DEFAULT CURRENT_TIMESTAMP,
				fechado_em TEXT
			)""")
			banco.execute("""CREATE TABLE IF NOT EXISTS pedido_mesa_itens (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				pedido_id INTEGER NOT NULL,
				insumo_id INTEGER NOT NULL,
				nome TEXT NOT NULL,
				quantidade REAL NOT NULL,
				preco_unitario REAL NOT NULL,
				subtotal REAL NOT NULL,
				FOREIGN KEY (pedido_id) REFERENCES pedidos_mesa(id),
				FOREIGN KEY (insumo_id) REFERENCES insumos(id)
			)""")
			banco.execute("""CREATE TABLE IF NOT EXISTS usuarios (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				usuario TEXT NOT NULL UNIQUE,
				senha TEXT NOT NULL,
				nivel TEXT NOT NULL DEFAULT 'basico'
			)""")
			colunas_usuarios = [linha[1] for linha in banco.execute("PRAGMA table_info(usuarios)").fetchall()]
			if "nivel" not in colunas_usuarios:
				banco.execute("ALTER TABLE usuarios ADD COLUMN nivel TEXT NOT NULL DEFAULT 'basico'")
			usuarios_iniciais = [("admin", "1234", "administrador"),
								("gerente", "1234", "gerente"), ("operador", "1234", "basico")]
			for usuario, senha, nivel in usuarios_iniciais:
				banco.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, nivel) VALUES (?, ?, ?)",
							  (usuario, hashlib.sha256(senha.encode()).hexdigest(), nivel))
			banco.execute("UPDATE usuarios SET nivel = 'administrador' WHERE usuario = 'admin'")
			banco.execute("""CREATE TABLE IF NOT EXISTS clientes (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				nome TEXT NOT NULL,
				telefone TEXT NOT NULL DEFAULT '',
				observacoes TEXT NOT NULL DEFAULT '',
				credito REAL NOT NULL DEFAULT 0,
				criado_em TEXT DEFAULT CURRENT_TIMESTAMP
			)""")
			banco.execute("""CREATE TABLE IF NOT EXISTS funcionarios (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				nome TEXT NOT NULL,
				cargo TEXT NOT NULL DEFAULT '',
				admissao TEXT NOT NULL DEFAULT '',
				salario REAL NOT NULL DEFAULT 0,
				comissao REAL NOT NULL DEFAULT 0,
				ativo INTEGER NOT NULL DEFAULT 1
			)""")
			banco.execute("""CREATE TABLE IF NOT EXISTS ponto_registros (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				funcionario_id INTEGER NOT NULL,
				data TEXT NOT NULL,
				entrada TEXT,
				inicio_intervalo TEXT,
				retorno_intervalo TEXT,
				saida TEXT,
				UNIQUE(funcionario_id, data),
				FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id)
			)""")
			banco.execute("""CREATE TABLE IF NOT EXISTS caixa_movimentos (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				tipo TEXT NOT NULL,
				forma_pagamento TEXT NOT NULL,
				valor REAL NOT NULL,
				observacao TEXT NOT NULL DEFAULT '',
				data TEXT DEFAULT CURRENT_TIMESTAMP
			)""")
		with self.conectar() as banco:
			for esquema, tabela in (("vendas_db", "vendas"), ("vendas_db", "venda_itens"),
									("pedidos_db", "pedidos_mesa"), ("pedidos_db", "pedido_mesa_itens")):
				banco.execute("CREATE TABLE IF NOT EXISTS " + esquema + "." + tabela +
					" AS SELECT * FROM main." + tabela + " WHERE 0")
			for tabela in ("vendas", "venda_itens", "pedidos_mesa", "pedido_mesa_itens"):
				banco.execute("DROP TABLE IF EXISTS " + tabela)

	def configurar_estilos(self):
		estilo = ttk.Style()
		estilo.theme_use("clam")
		estilo.configure("TLabel", font=("Segoe UI", 10), foreground=PALETA["texto"])
		estilo.configure("Treeview", rowheight=36, font=("Segoe UI", 10),
						 background=PALETA["superficie"], fieldbackground=PALETA["superficie"],
						 bordercolor=PALETA["borda"], lightcolor=PALETA["superficie"],
						 darkcolor="#CBD5E1", borderwidth=1, relief="flat")
		estilo.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"),
							 foreground="#475569", background="#F1F5F9",
						 bordercolor=PALETA["borda"], relief="flat")
		estilo.map("Treeview", background=[("selected", "#DBEAFE")],
				   foreground=[("selected", PALETA["texto"])])
		estilo.configure("TCombobox", padding=7, relief="flat", borderwidth=0,
						 foreground=PALETA["texto"], fieldbackground=PALETA["superficie"],
						 selectbackground=PALETA["primaria"])
		estilo.configure("TScrollbar", troughcolor="#F1F5F9", background="#CBD5E1",
						 arrowcolor=PALETA["texto"], bordercolor=PALETA["borda"])
		estilo.configure("TButton", font=("Segoe UI", 9, "bold"), padding=(12, 8),
						 foreground=PALETA["texto"], background=PALETA["superficie"], borderwidth=0)
		estilo.map("TButton", background=[("active", "#E8EEF8")])

	def fazer_backup_automatico(self):
		os.makedirs(PASTA_BACKUPS, exist_ok=True)
		momento = datetime.now().strftime("%Y%m%d_%H%M%S")
		caminho = os.path.join(PASTA_BACKUPS, "backup_automatico_" + momento + ".db")
		try:
			with self.conectar() as origem:
				with sqlite3.connect(caminho) as destino:
					origem.backup(destino)
			backups = sorted(
				(nome for nome in os.listdir(PASTA_BACKUPS) if nome.startswith("backup_automatico_") and nome.endswith(".db")),
				key=lambda nome: os.path.getmtime(os.path.join(PASTA_BACKUPS, nome)),
			)
			for nome in backups[:-10]:
				os.remove(os.path.join(PASTA_BACKUPS, nome))
			return caminho
		except (sqlite3.Error, OSError):
			return None

	def agendar_backup_automatico(self):
		self.fazer_backup_automatico()
		self.janela.after(300000, self.agendar_backup_automatico)

	def fechar_sistema(self):
		self.api.parar()
		self.fazer_backup_automatico()
		self.janela.destroy()

	def mostrar_conexao_api(self):
		janela = tk.Toplevel(self.janela)
		janela.title("Conexao do aplicativo - " + NOME_SISTEMA)
		janela.geometry("560x430")
		janela.resizable(False, False)
		janela.configure(bg="#f1f5f7")
		painel = tk.Frame(janela, bg="#ffffff", relief="raised", bd=2,
					  highlightbackground="#c2d5d2", highlightthickness=1)
		painel.pack(fill="both", expand=True, padx=18, pady=18)
		tk.Label(painel, text="Conexão do aplicativo", font=("Georgia", 20, "bold"),
				 foreground="#23343b", background="#ffffff").pack(anchor="w", padx=28, pady=(26, 4))
		tk.Label(painel, text="Use estes dados para conectar o aplicativo à rede Wi-Fi.",
				 font=("Segoe UI", 10), foreground="#71858a", background="#ffffff").pack(anchor="w", padx=30, pady=(0, 20))
		status = "API online" if self.api.servidor else "API indisponível"
		cor_status = "#16827c" if self.api.servidor else "#c94b43"
		tk.Label(painel, text="●  " + status, font=("Segoe UI", 10, "bold"),
				 foreground=cor_status, background="#ffffff").pack(anchor="w", padx=30, pady=(0, 14))

		try:
			socketo = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			socketo.connect(("8.8.8.8", 80))
			ip = socketo.getsockname()[0]
			socketo.close()
		except OSError:
			ip = socket.gethostbyname(socket.gethostname())
		endereco = "http://" + ip + ":8765"
		token = self.api.token

		def linha(rotulo, valor, sensivel=False):
			linha_frame = tk.Frame(painel, bg="#f7faf9", highlightbackground="#d6e2e0", highlightthickness=1)
			linha_frame.pack(fill="x", padx=28, pady=5)
			tk.Label(linha_frame, text=rotulo, font=("Segoe UI", 8, "bold"),
					 foreground="#62757a", background="#f7faf9").pack(side="left", padx=12, pady=10)
			valor_label = tk.Label(linha_frame, text=valor, font=("Consolas", 9),
						 foreground="#23343b", background="#f7faf9")
			valor_label.pack(side="left", padx=8)
			def copiar():
				janela.clipboard_clear()
				janela.clipboard_append(valor)
				status.config(text="●  Copiado para a área de transferência", foreground="#16827c")
			tk.Button(linha_frame, text="Copiar", command=copiar, relief="raised", bd=1,
					  bg="#ffffff", fg="#455a60", activebackground="#e7f0ef",
					  font=("Segoe UI", 8, "bold"), padx=8, pady=4).pack(side="right", padx=8)

		linha("ENDEREÇO", endereco)
		linha("PORTA", "8765")
		linha("TOKEN", token)
		def abrir_qrcode():
			dados = json.dumps({"url": endereco, "token": token}, ensure_ascii=False)
			url_qrcode = "https://api.qrserver.com/v1/create-qr-code/?size=420x420&data=" + quote(dados)
			webbrowser.open(url_qrcode)

		tk.Button(painel, text="▣  Abrir QR Code para conectar",
				 command=abrir_qrcode, relief="raised", bd=1, overrelief="sunken",
				 bg="#d45b45", fg="white", activebackground="#b84435",
				 activeforeground="white", font=("Segoe UI", 10, "bold"),
				 padx=16, pady=9, cursor="hand2").pack(fill="x", padx=28, pady=(16, 0))
		tk.Label(painel, text="O celular ou aplicativo precisa estar na mesma rede Wi-Fi.",
				 font=("Segoe UI", 8), foreground="#71858a", background="#ffffff").pack(anchor="w", padx=30, pady=(14, 0))

	def definir_tela_cheia(self):
		self.janela.attributes("-fullscreen", True)

	def definir_meia_tela(self):
		self.janela.attributes("-fullscreen", False)
		self.janela.state("normal")
		self.janela.update_idletasks()
		largura = max(1000, self.janela.winfo_screenwidth() // 2)
		altura = max(620, self.janela.winfo_screenheight() - 80)
		self.janela.geometry(str(largura) + "x" + str(altura) + "+0+0")

	def minimizar_janela(self):
		self.janela.iconify()

	def executar_com_permissao(self, nivel_necessario, comando):
		ordem = {"basico": 1, "gerente": 2, "administrador": 3}
		if ordem.get(self.nivel_acesso, 0) < ordem[nivel_necessario]:
			messagebox.showwarning("Acesso negado", "Seu perfil precisa ser '" + nivel_necessario + "' ou superior.")
			return
		comando()

	def criar_botao_menu_premium(self, pai, icone, texto, comando):
		botao = tk.Button(pai, text=icone + "   " + texto, command=comando, anchor="w",
						 relief="flat", bg=PALETA["sidebar"], fg="#DCE5F2",
						 activebackground=PALETA["sidebar_hover"], activeforeground="white",
						 font=("Segoe UI", 10), padx=18, pady=11, borderwidth=0,
						 highlightthickness=0, cursor="hand2")
		botao.pack(fill="x", padx=10, pady=2)
		botao.bind("<Enter>", lambda _: botao.configure(bg=PALETA["sidebar_hover"]), add="+")
		botao.bind("<Leave>", lambda _: botao.configure(bg=PALETA["sidebar"]), add="+")
		return botao

	def mostrar_carregando(self, ativo=True):
		if not hasattr(self, "status_app"):
			return
		if ativo:
			self._spinner_frame = getattr(self, "_spinner_frame", 0) + 1
			self.status_app.config(text="Carregando" + "." * (self._spinner_frame % 4), foreground=PALETA["primaria"])
			self.janela.after(120, lambda: self.mostrar_carregando(True) if getattr(self, "_carregando", False) else None)
		else:
			self._carregando = False
			self.status_app.config(text="Sistema conectado", foreground=PALETA["muted"])

	def mostrar_feedback(self, mensagem, cor=None):
		if hasattr(self, "status_app"):
			self.status_app.config(text=mensagem, foreground=cor or PALETA["sucesso"])
			self.janela.after(2800, lambda: self.status_app.config(text="Sistema conectado", foreground=PALETA["muted"]) if self.status_app.winfo_exists() else None)

	def alternar_tema(self, escuro):
		self.tema_escuro = escuro
		self.aplicar_tema(self.janela)
		self.mostrar_feedback("Tema escuro ativado" if escuro else "Tema claro ativado", PALETA["primaria"])

	def aplicar_tema(self, widget):
		paleta_tema = PALETA_ESCURA if self.tema_escuro else PALETA
		mapeamento = {
			"#F4F7FB": paleta_tema["fundo"], "#f1f5f7": paleta_tema["fundo"],
			"#FFFFFF": paleta_tema["superficie"], "#ffffff": paleta_tema["superficie"],
			"#0B1220": paleta_tema["fundo"], "#111C2E": paleta_tema["superficie"],
			"#0F172A": paleta_tema["texto"], "#23343b": paleta_tema["texto"],
			"#1f2d35": paleta_tema["texto"], "#64748B": paleta_tema["muted"],
			"#62757a": paleta_tema["muted"], "#E2E8F0": paleta_tema["borda"],
			"#d6e2e0": paleta_tema["borda"], "#172a33": paleta_tema["sidebar"],
			"#101827": paleta_tema["sidebar"], "#070D18": paleta_tema["sidebar"],
		}
		try:
			configuracao = widget.configure()
			for propriedade in ("background", "bg", "highlightbackground"):
				if propriedade in configuracao:
					valor = widget.cget(propriedade)
					if valor in mapeamento:
						widget.configure(**{propriedade: mapeamento[valor]})
			for propriedade in ("foreground", "fg", "highlightcolor"):
				if propriedade in configuracao:
					valor = widget.cget(propriedade)
					if valor in mapeamento:
						widget.configure(**{propriedade: mapeamento[valor]})
		except tk.TclError:
			pass
		for filho in widget.winfo_children():
			self.aplicar_tema(filho)

	def criar_tela_premium(self):
		menu = tk.Frame(self.janela, bg=PALETA["sidebar"], width=238)
		menu.pack(side="left", fill="y")
		menu.pack_propagate(False)
		marca = tk.Frame(menu, bg=PALETA["sidebar"], height=110)
		marca.pack(fill="x")
		marca.pack_propagate(False)
		tk.Label(marca, text=NOME_SISTEMA, font=("Segoe UI", 20, "bold"),
				 foreground="#FFFFFF", background=PALETA["sidebar"]).pack(anchor="w", padx=22, pady=(22, 0))
		tk.Label(marca, text="GESTAO INTELIGENTE", font=("Segoe UI", 8, "bold"),
				 foreground="#91A4BF", background=PALETA["sidebar"]).pack(anchor="w", padx=24, pady=(2, 0))
		tk.Frame(menu, height=1, bg="#26344A").pack(fill="x", padx=22, pady=(0, 17))
		tk.Label(menu, text="NAVEGACAO", font=("Segoe UI", 8, "bold"),
				 foreground=PALETA["sidebar_muted"], background=PALETA["sidebar"]).pack(anchor="w", padx=24, pady=(0, 7))
		self.criar_botao_menu_premium(menu, "⌂", "Início", self.mostrar_painel_premium)
		self.criar_botao_menu_premium(menu, "▣", "Vendas", self.abrir_vendas)
		self.criar_botao_menu_premium(menu, "▦", "Pedidos Mesas", self.abrir_pedidos_mesa)
		self.criar_botao_menu_premium(menu, "◈", "Estoque", self.abrir_controle_estoque)
		self.criar_botao_menu_premium(menu, "◔", "Relatórios", self.mostrar_historico)
		self.criar_botao_menu_premium(menu, "⚙", "Configurações", self.mostrar_conexao_api)
		rodape = tk.Frame(menu, bg=PALETA["sidebar"])
		rodape.pack(side="bottom", fill="x", padx=22, pady=20)
		tk.Label(rodape, text=self.usuario_logado + "  |  " + self.nivel_acesso,
				 font=("Segoe UI", 9, "bold"), foreground="#DCE5F2", background=PALETA["sidebar"]).pack(anchor="w")
		tk.Label(rodape, text="API Wi-Fi online  |  8765", font=("Segoe UI", 8),
				 foreground=PALETA["sidebar_muted"], background=PALETA["sidebar"]).pack(anchor="w", pady=(4, 0))

		principal = tk.Frame(self.janela, bg=PALETA["fundo"])
		principal.pack(side="left", fill="both", expand=True)
		barra = tk.Frame(principal, bg=PALETA["superficie"], height=70)
		barra.pack(fill="x", padx=24, pady=(20, 0))
		barra.pack_propagate(False)
		tk.Label(barra, text="Visao geral", font=("Segoe UI", 17, "bold"),
				 foreground=PALETA["texto"], background=PALETA["superficie"]).pack(side="left", padx=22)
		controles_tema = tk.Frame(barra, bg=PALETA["superficie"])
		controles_tema.pack(side="right", padx=(0, 12))
		botao_sol = tk.Button(controles_tema, text="☀", command=lambda: self.alternar_tema(False),
						 relief="flat", bd=0, bg=PALETA["superficie"], fg="#E59A22",
						 activebackground="#FFF7E6", activeforeground="#C77B08",
						 font=("Segoe UI Symbol", 16), width=2, cursor="hand2")
		botao_sol.pack(side="left", padx=2)
		botao_lua = tk.Button(controles_tema, text="☾", command=lambda: self.alternar_tema(True),
						 relief="flat", bd=0, bg=PALETA["superficie"], fg="#526581",
						 activebackground="#E8EEF8", activeforeground="#263A5A",
						 font=("Segoe UI Symbol", 17), width=2, cursor="hand2")
		botao_lua.pack(side="left", padx=2)
		botao_sol.bind("<Enter>", lambda _: botao_sol.configure(bg="#FFF7E6"), add="+")
		botao_sol.bind("<Leave>", lambda _: botao_sol.configure(bg=PALETA["superficie"]), add="+")
		botao_lua.bind("<Enter>", lambda _: botao_lua.configure(bg="#E8EEF8"), add="+")
		botao_lua.bind("<Leave>", lambda _: botao_lua.configure(bg=PALETA["superficie"]), add="+")
		self.status_app = tk.Label(barra, text="Sistema conectado", font=("Segoe UI", 9),
				 foreground=PALETA["muted"], background=PALETA["superficie"])
		self.status_app.pack(side="right", padx=22)
		self.estabelecimento = tk.StringVar(value="Churrascaria")
		self.area_principal = tk.Frame(principal, bg=PALETA["fundo"])
		self.area_principal.pack(fill="both", expand=True)
		self.mostrar_painel_premium()

	def mostrar_painel_premium(self):
		for widget in self.area_principal.winfo_children():
			widget.destroy()
		self._carregando = True
		self.mostrar_carregando(True)
		conteudo = tk.Frame(self.area_principal, bg=PALETA["fundo"])
		conteudo.pack(fill="both", expand=True, padx=30, pady=28)
		tk.Label(conteudo, text="Bom dia, " + self.usuario_logado + ".", font=("Segoe UI", 25, "bold"),
				 foreground=PALETA["texto"], background=PALETA["fundo"]).pack(anchor="w")
		tk.Label(conteudo, text="Acompanhe os pontos mais importantes da sua operacao.", font=("Segoe UI", 10),
				 foreground=PALETA["muted"], background=PALETA["fundo"]).pack(anchor="w", pady=(3, 24))
		with self.conectar() as banco:
			vendas = banco.execute("SELECT COALESCE(SUM(total), 0) FROM vendas_db.vendas WHERE date(data, 'localtime') = date('now', 'localtime') AND estabelecimento = ?", (self.estabelecimento.get(),)).fetchone()[0]
			abertos = banco.execute("SELECT COUNT(*) FROM pedidos_db.pedidos_mesa WHERE status = 'aberto' AND estabelecimento = ?", (self.estabelecimento.get(),)).fetchone()[0]
			baixos = banco.execute("SELECT COUNT(*) FROM main.insumos WHERE estabelecimento = ? AND origem = 'estoque' AND quantidade <= estoque_minimo", (self.estabelecimento.get(),)).fetchone()[0]
		indicadores = tk.Frame(conteudo, bg=PALETA["fundo"])
		indicadores.pack(fill="x", pady=(0, 30))
		for titulo, valor, detalhe, cor in (("Vendas do dia", self.formatar_moeda(vendas), "Total realizado hoje", PALETA["primaria"]),
										 ("Pedidos em aberto", str(abertos), "Mesas aguardando fechamento", "#0F9D78"),
										 ("Estoque baixo", str(baixos), "Itens abaixo do minimo", "#E58A24")):
			cartao = tk.Frame(indicadores, bg=PALETA["superficie"], highlightbackground=PALETA["borda"], highlightthickness=1)
			cartao.pack(side="left", fill="both", expand=True, padx=(0, 12))
			tk.Label(cartao, text=titulo.upper(), font=("Segoe UI", 8, "bold"), foreground=PALETA["muted"], background=PALETA["superficie"]).pack(anchor="w", padx=18, pady=(17, 3))
			tk.Label(cartao, text=valor, font=("Segoe UI", 21, "bold"), foreground=cor, background=PALETA["superficie"]).pack(anchor="w", padx=18)
			tk.Label(cartao, text=detalhe, font=("Segoe UI", 9), foreground=PALETA["muted"], background=PALETA["superficie"]).pack(anchor="w", padx=18, pady=(2, 17))
		tk.Label(conteudo, text="Acesso rapido", font=("Segoe UI", 12, "bold"), foreground=PALETA["texto"], background=PALETA["fundo"]).pack(anchor="w", pady=(0, 12))
		atalhos = tk.Frame(conteudo, bg=PALETA["fundo"])
		atalhos.pack(fill="x")
		for titulo, descricao, icone, comando, cor in (("Vendas", "Registre e acompanhe suas vendas", "▣", self.abrir_vendas, PALETA["primaria"]),
										 ("Estoque", "Controle produtos e inventario", "◈", self.abrir_controle_estoque, "#0F9D78"),
										 ("Pedidos Mesas", "Acompanhe as mesas em aberto", "▦", self.abrir_pedidos_mesa, "#E58A24")):
			cartao = tk.Frame(atalhos, bg=PALETA["superficie"], highlightbackground=PALETA["borda"], highlightthickness=1, cursor="hand2")
			cartao.pack(side="left", fill="both", expand=True, padx=(0, 12))
			tk.Label(cartao, text=icone, font=("Segoe UI Symbol", 22), foreground=cor, background=PALETA["superficie"]).pack(anchor="w", padx=18, pady=(18, 2))
			tk.Label(cartao, text=titulo, font=("Segoe UI", 12, "bold"), foreground=PALETA["texto"], background=PALETA["superficie"]).pack(anchor="w", padx=18)
			tk.Label(cartao, text=descricao, font=("Segoe UI", 9), foreground=PALETA["muted"], background=PALETA["superficie"]).pack(anchor="w", padx=18, pady=(3, 18))
			for widget in (cartao, *cartao.winfo_children()):
				widget.bind("<Button-1>", lambda _, acao=comando: acao(), add="+")
		self.mostrar_carregando(False)

	def criar_tela(self):
		menu = tk.Frame(self.janela, bg="#172a33", width=224)
		menu.pack(side="left", fill="y")
		menu.pack_propagate(False)
		cabecalho_menu = tk.Frame(menu, bg="#172a33", height=46)
		cabecalho_menu.pack(side="top", fill="x")
		cabecalho_menu.pack_propagate(False)
		menu_aberto = [True]
		area_menu = tk.Frame(menu, bg="#172a33")
		area_menu.pack(side="top", fill="both", expand=True)
		canvas_menu = tk.Canvas(area_menu, bg="#172a33", highlightthickness=0, bd=0)
		barra_menu = ttk.Scrollbar(area_menu, orient="vertical", command=canvas_menu.yview)
		canvas_menu.configure(yscrollcommand=barra_menu.set)
		canvas_menu.pack(side="left", fill="both", expand=True)
		barra_menu.pack(side="right", fill="y")
		conteudo_menu = tk.Frame(canvas_menu, bg="#172a33")
		janela_menu = canvas_menu.create_window((0, 0), window=conteudo_menu, anchor="nw")
		conteudo_menu.bind("<Configure>", lambda _: canvas_menu.configure(scrollregion=canvas_menu.bbox("all")))
		canvas_menu.bind("<Configure>", lambda evento: canvas_menu.itemconfigure(janela_menu, width=evento.width))

		def rolar_menu(evento):
			widget = self.janela.winfo_containing(evento.x_root, evento.y_root)
			while widget:
				if widget in (canvas_menu, conteudo_menu):
					direcao = -3 if getattr(evento, "num", 0) == 4 or evento.delta > 0 else 3
					canvas_menu.yview_scroll(direcao, "units")
					return "break"
				widget = widget.master

		self.janela.bind_all("<MouseWheel>", rolar_menu, add="+")
		self.janela.bind_all("<Button-4>", rolar_menu, add="+")
		self.janela.bind_all("<Button-5>", rolar_menu, add="+")
		status_menu = []

		def alternar_menu():
			menu_aberto[0] = not menu_aberto[0]
			if menu_aberto[0]:
				menu.configure(width=224)
				area_menu.pack(side="top", fill="both", expand=True)
				for widget in status_menu:
					widget.pack(**widget._pack_info_original)
				botao_menu.configure(text="☰  MENU", anchor="w")
			else:
				area_menu.pack_forget()
				menu.configure(width=52)
				for widget in status_menu:
					widget.pack_forget()
				botao_menu.configure(text="☰", anchor="center")

		botao_menu = tk.Button(cabecalho_menu, text="☰  MENU", command=alternar_menu,
					bg="#214b55", fg="#f7fbfa", activebackground="#34717a",
					activeforeground="white", font=("Segoe UI", 11, "bold"),
					borderwidth=0, relief="flat", cursor="hand2", anchor="w",
					highlightthickness=1, highlightbackground="#3f7278",
					padx=10)
		botao_menu.pack(fill="both", expand=True, padx=6, pady=6)
		tk.Label(conteudo_menu, text=NOME_SISTEMA, font=("Georgia", 19, "bold"),
				 fg="#f0bf62", bg="#172a33").pack(anchor="w", padx=28, pady=(30, 2))
		tk.Label(conteudo_menu, text="GESTAO INTEGRADA", font=("Segoe UI", 8, "bold"),
				 fg="#9db8ba", bg="#172a33").pack(anchor="w", padx=29, pady=(0, 35))
		tk.Label(conteudo_menu, text="ACESSO RAPIDO", font=("Segoe UI", 8, "bold"),
				 fg="#f0bf62", bg="#172a33").pack(anchor="w", padx=29, pady=(0, 6))
		tk.Frame(conteudo_menu, bg="#3f7278", height=2).pack(fill="x", padx=28, pady=(0, 9))
		tk.Label(conteudo_menu, text="MODULOS DE GESTAO", font=("Segoe UI", 8, "bold"),
				 fg="#f0bf62", bg="#172a33").pack(anchor="w", padx=29, pady=(0, 6))
		modulos = tk.Frame(conteudo_menu, bg="#172a33")
		modulos.pack(fill="x", padx=8)
		for texto, comando in (("Início", self.mostrar_painel_inicial),
							("Estoque", self.abrir_controle_estoque),
							("Vendas", self.abrir_vendas),
							("Mesas / Pedidos", self.abrir_pedidos_mesa),
							("Caixa", self.abrir_caixa),
							("Clientes", self.abrir_clientes),
							("Funcionários", self.abrir_funcionarios)):
			tk.Button(modulos, text="›  " + texto, command=comando, anchor="w", relief="raised",
					bg="#214b55", fg="#f7fbfa", activebackground="#34717a",
					activeforeground="white", font=("Segoe UI", 10, "bold"), padx=16, pady=10,
					borderwidth=1, highlightthickness=1, highlightbackground="#4a8490",
					overrelief="sunken").pack(fill="x", pady=3)
		opcoes = [("Painel geral", self.atualizar_tela),
				  ("Conexão do aplicativo", self.mostrar_conexao_api),
				  ("Cadastrar insumo", lambda: self.executar_com_permissao("gerente", self.abrir_cadastro)),
				  ("Registrar entrada / saída", lambda: self.executar_com_permissao("gerente", self.abrir_movimentacao)),
				  ("Histórico de movimentações", self.mostrar_historico),
				  ("Exportar estoque CSV", self.exportar_csv),
				  ("Exportar para Excel", self.exportar_excel),
				  ("Baixar PDF para o usuário", self.baixar_pdf),
				  ("Fazer backup do banco", lambda: self.executar_com_permissao("administrador", self.fazer_backup)),
				  ("Backup automático agora", lambda: self.executar_com_permissao("administrador", self.fazer_backup_automatico)),
				  ("Restaurar backup", lambda: self.executar_com_permissao("administrador", self.restaurar_backup)),
				  ("Atualizar estoque", self.atualizar_tela)]
		for texto, comando in opcoes:
			tk.Button(conteudo_menu, text="  " + texto, command=comando, anchor="w", relief="flat",
					  bg="#172a33", fg="#e7f0ef", activebackground="#214b55",
					  activeforeground="white", font=("Segoe UI", 9), padx=15, pady=10,
					  borderwidth=0).pack(fill="x", padx=12, pady=2)
		for texto, fonte, cor, margem in (
				("Usuário: " + self.usuario_logado + " | " + self.nivel_acesso, ("Segoe UI", 8), "#91abad", (0, 4)),
				("●  Sistema conectado", ("Segoe UI", 9), "#64b5a8", 25),
				("API Wi-Fi  •  porta 8765", ("Segoe UI", 8), "#91abad", (0, 4))):
			widget = tk.Label(menu, text=texto, font=fonte, fg=cor, bg="#172a33")
			widget._pack_info_original = {"side": "bottom", "anchor": "w", "padx": 29, "pady": margem}
			widget.pack(**widget._pack_info_original)
			status_menu.append(widget)

		principal = tk.Frame(self.janela, bg=PALETA["fundo"])
		principal.pack(side="left", fill="both", expand=True)
		barra_superior = tk.Frame(principal, bg="#ffffff", height=68,
						 highlightbackground="#dce8e5", highlightthickness=1)
		barra_superior.pack(fill="x", padx=18, pady=(14, 0))
		barra_superior.pack_propagate(False)
		cabecalho = tk.Frame(barra_superior, bg="#ffffff")
		cabecalho.pack(side="left", fill="y", padx=20)
		tk.Label(cabecalho, text=NOME_SISTEMA, font=("Segoe UI", 14, "bold"),
				 foreground="#23343b", background="#ffffff").pack(anchor="w", pady=(13, 0))
		tk.Label(cabecalho, text=DESCRICAO_SISTEMA.upper(), font=("Segoe UI", 8, "bold"),
				 foreground="#16827c", background="#ffffff").pack(anchor="w")
		status_superior = tk.Frame(barra_superior, bg="#ffffff")
		status_superior.pack(side="right", fill="y", padx=20)
		tk.Label(status_superior, text="●  API online", font=("Segoe UI", 9, "bold"),
				 foreground="#16827c", background="#ffffff").pack(side="left", padx=(0, 18), pady=23)
		tk.Label(status_superior, text=self.usuario_logado + "  /  " + self.nivel_acesso,
				 font=("Segoe UI", 9), foreground="#62757a", background="#ffffff").pack(side="left", pady=23)
		area_principal = tk.Frame(principal, bg=PALETA["fundo"])
		area_principal.pack(fill="both", expand=True)
		self.area_principal = area_principal
		self.estabelecimento = tk.StringVar(value="Churrascaria")
		self.mostrar_painel_inicial()

	def mostrar_painel_inicial(self):
		for widget in self.area_principal.winfo_children():
			widget.destroy()
		topo = tk.Frame(self.area_principal, bg=PALETA["fundo"])
		topo.pack(fill="x", padx=30, pady=(28, 14))
		tk.Frame(topo, bg="#d45b45", height=4, width=54).pack(anchor="w", pady=(0, 10))
		cabecalho = tk.Frame(topo, bg=PALETA["fundo"])
		cabecalho.pack(side="left")
		tk.Label(cabecalho, text="Bem-vindo ao " + NOME_SISTEMA, font=("Segoe UI", 25, "bold"),
				 foreground=PALETA["texto"], background=PALETA["fundo"]).pack(anchor="w")
		tk.Label(cabecalho, text=DESCRICAO_SISTEMA + ".",
				 font=("Segoe UI", 10), foreground=PALETA["muted"], background=PALETA["fundo"]).pack(anchor="w", pady=(3, 0))

		linha_modulos = tk.Frame(self.area_principal, bg=PALETA["fundo"])
		linha_modulos.pack(fill="x", padx=32, pady=(0, 10))
		tk.Label(linha_modulos, text="Acesso rápido", font=("Segoe UI", 11, "bold"),
				 foreground=PALETA["texto"], background=PALETA["fundo"]).pack(side="left")
		tk.Frame(linha_modulos, bg="#c9d8d8", height=1).pack(side="left", fill="x", expand=True, padx=(14, 0), pady=4)
		atalhos = tk.Frame(self.area_principal, bg=PALETA["fundo"])
		atalhos.pack(fill="x", padx=25, pady=(0, 28))
		self.criar_cartao_modulo(atalhos, "CONTROLE DE\nESTOQUE", "Produtos e inventário", self.abrir_controle_estoque, PALETA["primaria"])
		self.criar_cartao_modulo(atalhos, "VENDAS", "Registre e acompanhe vendas", self.abrir_vendas, "#168a5b")
		self.criar_cartao_modulo(atalhos, "PEDIDOS DA\nMESA", "Acompanhe pedidos em aberto", self.abrir_pedidos_mesa, "#e0a13a")

	def criar_botao_voltar(self, pai, margem):
		botao = tk.Button(pai, text="‹  Painel inicial", command=self.mostrar_painel_inicial,
					 relief="raised", bd=1, overrelief="sunken", bg="#ffffff", fg="#455a60",
					 activebackground="#e7f0ef", activeforeground="#1f2d35",
					 highlightthickness=1, highlightbackground="#c2d5d2",
					 font=("Segoe UI", 9, "bold"), padx=13, pady=7, cursor="hand2")
		botao.pack(anchor="ne", padx=margem, pady=(18, 0))
		botao.bind("<Enter>", lambda _: botao.configure(relief="sunken", fg="#16827c", highlightbackground="#16827c"), add="+")
		botao.bind("<Leave>", lambda _: botao.configure(relief="raised", fg="#455a60", highlightbackground="#c2d5d2"), add="+")

	def abrir_modulo_gestao(self, titulo, descricao, grupos, comando_ponto=None):
		for widget in self.area_principal.winfo_children():
			widget.destroy()
		janela = tk.Frame(self.area_principal, bg="#f1f5f7")
		janela.pack(fill="both", expand=True)
		self.criar_botao_voltar(janela, 30)
		tk.Label(janela, text=titulo, font=("Georgia", 25, "bold"),
				 foreground="#23343b", background="#f1f5f7").pack(anchor="w", padx=30, pady=(22, 2))
		tk.Label(janela, text=descricao, font=("Segoe UI", 10),
				 foreground="#62757a", background="#f1f5f7").pack(anchor="w", padx=32, pady=(0, 18))
		area_externa = tk.Frame(janela, bg="#f1f5f7")
		area_externa.pack(fill="both", expand=True, padx=30, pady=(0, 28))
		canvas_modulo = tk.Canvas(area_externa, bg="#f1f5f7", highlightthickness=0)
		barra_modulo = ttk.Scrollbar(area_externa, orient="vertical", command=canvas_modulo.yview)
		canvas_modulo.configure(yscrollcommand=barra_modulo.set)
		canvas_modulo.pack(side="left", fill="both", expand=True)
		barra_modulo.pack(side="right", fill="y")
		area = tk.Frame(canvas_modulo, bg="#f1f5f7")
		janela_modulo = canvas_modulo.create_window((0, 0), window=area, anchor="nw")
		area.bind("<Configure>", lambda _: canvas_modulo.configure(scrollregion=canvas_modulo.bbox("all")))
		canvas_modulo.bind("<Configure>", lambda evento: canvas_modulo.itemconfigure(janela_modulo, width=evento.width))

		def rolar_modulo(evento):
			widget = self.janela.winfo_containing(evento.x_root, evento.y_root)
			while widget:
				if widget in (canvas_modulo, area):
					direcao = -1 if getattr(evento, "num", 0) == 4 or getattr(evento, "delta", 0) > 0 else 1
					canvas_modulo.yview_scroll(direcao, "units")
					return "break"
				widget = widget.master
		self.janela.bind_all("<MouseWheel>", rolar_modulo, add="+")
		self.janela.bind_all("<Button-4>", rolar_modulo, add="+")
		self.janela.bind_all("<Button-5>", rolar_modulo, add="+")
		for indice, (grupo, itens) in enumerate(grupos):
			coluna = indice % 2
			linha = indice // 2
			cartao = tk.Frame(area, bg="#ffffff", highlightbackground="#d6e2e0", highlightthickness=1)
			cartao.grid(row=linha, column=coluna, sticky="nsew", padx=(0 if coluna == 0 else 8, 8 if coluna == 0 else 0), pady=(0, 12))
			tk.Label(cartao, text=grupo, font=("Segoe UI", 12, "bold"),
					foreground="#1f2d35", background="#ffffff").pack(anchor="w", padx=18, pady=(15, 8))
			for item in itens:
				if item in ("Controle de ponto", "Controle de entrada e saída", "Horas trabalhadas") and comando_ponto:
					comando = comando_ponto
				elif item == "Novo funcionário":
					comando = self.abrir_cadastro_funcionario
				elif item == "Ver funcionários cadastrados":
					comando = self.abrir_lista_funcionarios
				elif item == "Novo cliente":
					comando = self.abrir_cadastro_cliente
				else:
					comando = self.mostrar_funcionalidade
				linha_funcao = tk.Frame(cartao, bg="#f4f8f7")
				linha_funcao.pack(fill="x", padx=14, pady=2)
				tk.Button(linha_funcao, text="  " + item, command=lambda nome=item, acao=comando: acao(nome),
						relief="flat", anchor="w", bg="#f4f8f7", fg="#455a60",
						activebackground="#e0eeeb", font=("Segoe UI", 10), padx=12, pady=7,
						borderwidth=0).pack(side="left", fill="x", expand=True)
				tk.Button(linha_funcao, text="PDF", command=lambda modulo=titulo, secao=grupo, nome=item:
						self.baixar_pdf_funcao(modulo, secao, nome), relief="flat", bg="#e5efed", fg="#16827c",
						activebackground="#cfe5e1", font=("Segoe UI", 8, "bold"), padx=8, pady=7,
						borderwidth=0).pack(side="right", padx=(4, 0))
			if not itens:
				tk.Label(cartao, text="Nenhum recurso cadastrado ainda.", font=("Segoe UI", 9),
						foreground="#8a9a9d", background="#ffffff").pack(anchor="w", padx=18, pady=(0, 15))
		for coluna in range(2):
			area.grid_columnconfigure(coluna, weight=1)
		for linha in range((len(grupos) + 1) // 2):
			area.grid_rowconfigure(linha, weight=1)

	def mostrar_funcionalidade(self, nome):
		messagebox.showinfo("NEXA", nome + " será disponibilizado nesta área do sistema.", parent=self.janela)

	def baixar_pdf_funcao(self, modulo, grupo, funcao):
		momento = datetime.now()
		nome_arquivo = "nexa_" + modulo.lower().replace(" ", "_") + "_" + funcao.lower().replace(" ", "_") + ".pdf"
		linhas = [
			NOME_SISTEMA + " - " + modulo.upper(),
			"Funcao: " + funcao,
			"Categoria: " + grupo,
			"Estabelecimento: " + self.estabelecimento.get(),
			"Usuario: " + self.usuario_logado,
			"Gerado em: " + momento.strftime("%d/%m/%Y %H:%M"),
			"",
			"Relatorio da funcao selecionada no sistema.",
		]
		caminho = os.path.join(os.path.dirname(ARQUIVO_BANCO), nome_arquivo)
		conteudo = ["BT", "/F1 11 Tf", "40 800 Td", "16 TL"]
		for linha in linhas:
			texto = linha.encode("latin-1", "replace").decode("latin-1")
			texto = texto.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
			conteudo.append("({}) Tj T*".format(texto))
		conteudo.append("ET")
		conteudo_bytes = "\n".join(conteudo).encode("latin-1")
		objetos = {
			1: b"<< /Type /Catalog /Pages 2 0 R >>",
			2: b"<< /Type /Pages /Kids [4 0 R] /Count 1 >>",
			3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
			4: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
			5: b"<< /Length " + str(len(conteudo_bytes)).encode() + b" >>\nstream\n" + conteudo_bytes + b"\nendstream",
		}
		pdf = bytearray(b"%PDF-1.4\n")
		offsets = [0] * 6
		for numero in range(1, 6):
			offsets[numero] = len(pdf)
			pdf.extend(str(numero).encode() + b" 0 obj\n" + objetos[numero] + b"\nendobj\n")
		xref = len(pdf)
		pdf.extend(b"xref\n0 6\n0000000000 65535 f \n")
		for numero in range(1, 6):
			pdf.extend(("{:010d} 00000 n \n".format(offsets[numero])).encode())
		pdf.extend(("trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{}\n%%EOF".format(xref)).encode())
		with open(caminho, "wb") as arquivo:
			arquivo.write(pdf)
		destino = filedialog.asksaveasfilename(title="Baixar PDF - " + funcao, defaultextension=".pdf",
				initialfile=nome_arquivo, filetypes=(("Arquivo PDF", "*.pdf"), ("Todos os arquivos", "*.*")))
		if destino:
			shutil.copyfile(caminho, destino)
			messagebox.showinfo("PDF salvo", "O PDF foi salvo em:\n" + destino, parent=self.janela)

	def abrir_caixa(self):
		self.abrir_modulo_gestao("Caixa", "Controle financeiro diário e conferência dos recebimentos.", (
			("Movimento", ("Abertura", "Sangria", "Suprimento", "Fechamento", "Conferência")),
			("Recebimentos", ("Dinheiro", "Pix", "Débito", "Crédito")),
			("Consultas", ("Resumo do caixa", "Histórico de movimentações"))))

	def abrir_clientes(self):
		self.abrir_modulo_gestao("Clientes", "Relacionamento, histórico de compras e condições comerciais.", (
			("Cadastro", ("Novo cliente", "Lista de clientes")),
			("Relacionamento", ("Histórico de compras", "Preferências", "Crédito / fiado"))))

	def abrir_cadastro_cliente(self, _=None):
		nome = simpledialog.askstring("Novo cliente", "Nome do cliente:", parent=self.janela)
		if not nome or not nome.strip():
			return
		telefone = simpledialog.askstring("Novo cliente", "Telefone:", parent=self.janela) or ""
		with self.conectar() as banco:
			banco.execute("INSERT INTO clientes (nome, telefone) VALUES (?, ?)", (nome.strip(), telefone.strip()))
		messagebox.showinfo("Cliente cadastrado", "O cliente foi cadastrado com sucesso.", parent=self.janela)

	def abrir_funcionarios(self):
		self.abrir_modulo_gestao("Funcionários", "Equipe, dados financeiros e jornada de trabalho.", (
			("Cadastro", ("Novo funcionário", "Ver funcionários cadastrados", "Cargo", "Data de admissão", "Salário / base", "Comissão")),
			("Financeiro", ("Extras", "Adiantamentos", "Faltas", "Atrasos", "Histórico financeiro")),
			("Jornada", ("Controle de entrada e saída", "Horas trabalhadas", "Controle de ponto"))),
			comando_ponto=self.abrir_controle_ponto)

	def abrir_lista_funcionarios(self, _=None):
		for widget in self.area_principal.winfo_children():
			widget.destroy()
		janela = tk.Frame(self.area_principal, bg="#f1f5f7")
		janela.pack(fill="both", expand=True)
		self.criar_botao_voltar(janela, 30)
		tk.Label(janela, text="Funcionários cadastrados", font=("Georgia", 25, "bold"),
				 foreground="#23343b", background="#f1f5f7").pack(anchor="w", padx=30, pady=(22, 2))
		tk.Label(janela, text="Consulte, edite ou remova os cadastros da equipe.", font=("Segoe UI", 10),
				 foreground="#62757a", background="#f1f5f7").pack(anchor="w", padx=32, pady=(0, 18))
		area = tk.Frame(janela, bg="#ffffff", highlightbackground="#d6e2e0", highlightthickness=1)
		area.pack(fill="both", expand=True, padx=30, pady=(0, 28))
		colunas = ("id", "nome", "cargo", "admissao", "salario", "comissao", "status")
		tabela = ttk.Treeview(area, columns=colunas, show="headings", selectmode="browse")
		cabecalhos = {"id": "ID", "nome": "NOME", "cargo": "CARGO", "admissao": "ADMISSAO",
						"salario": "SALARIO / BASE", "comissao": "COMISSAO", "status": "STATUS"}
		larguras = {"id": 45, "nome": 220, "cargo": 150, "admissao": 110, "salario": 130, "comissao": 100, "status": 90}
		for coluna in colunas:
			tabela.heading(coluna, text=cabecalhos[coluna])
			tabela.column(coluna, width=larguras[coluna], anchor="w")
		tabela.pack(side="left", fill="both", expand=True, padx=15, pady=15)
		rolagem = ttk.Scrollbar(area, orient="vertical", command=tabela.yview)
		rolagem.pack(side="right", fill="y", pady=15)
		tabela.configure(yscrollcommand=rolagem.set)

		def atualizar():
			for item in tabela.get_children():
				tabela.delete(item)
			with self.conectar() as banco:
				funcionarios = banco.execute("SELECT id, nome, cargo, admissao, salario, comissao, ativo FROM funcionarios ORDER BY nome").fetchall()
			for funcionario in funcionarios:
				tabela.insert("", "end", values=(funcionario["id"], funcionario["nome"], funcionario["cargo"],
					funcionario["admissao"], self.formatar_moeda(funcionario["salario"]),
					self.formatar_numero(funcionario["comissao"]) + "%", "Ativo" if funcionario["ativo"] else "Inativo"))

		def selecionado():
			itens_selecionados = tabela.selection()
			if not itens_selecionados:
				messagebox.showwarning("Nenhum funcionário selecionado", "Selecione um funcionário na tabela.", parent=janela)
				return None
			return tabela.item(itens_selecionados[0], "values")

		acoes = tk.Frame(janela, bg="#f1f5f7")
		acoes.pack(fill="x", padx=30, pady=(0, 18))
		botao_editar = tk.Button(acoes, text="✎", command=lambda: editar(), relief="flat", bg="#4c7a99", fg="white",
				activebackground="#355d78", font=("Segoe UI", 14, "bold"), padx=14, pady=4)
		botao_editar.pack(side="left", padx=(0, 8))
		botao_editar.bind("<Enter>", lambda _: botao_editar.configure(text="✎  Editar"), add="+")
		botao_editar.bind("<Leave>", lambda _: botao_editar.configure(text="✎"), add="+")
		tk.Button(acoes, text="Excluir selecionado", command=lambda: excluir(), relief="flat", bg="#bd4038", fg="white",
				activebackground="#8f2c28", font=("Segoe UI", 9, "bold"), padx=14, pady=8).pack(side="left")
		tabela.bind("<Double-1>", lambda _: editar())

		def editar():
			if self.nivel_acesso not in ("gerente", "administrador"):
				return self.executar_com_permissao("gerente", editar)
			registro = selecionado()
			if registro:
				self.editar_funcionario(registro, atualizar)

		def excluir():
			if self.nivel_acesso != "administrador":
				return self.executar_com_permissao("administrador", excluir)
			registro = selecionado()
			if not registro or not messagebox.askyesno("Excluir funcionário", "Excluir '" + registro[1] + "' do cadastro?", parent=janela):
				return
			with self.conectar() as banco:
				banco.execute("DELETE FROM ponto_registros WHERE funcionario_id = ?", (registro[0],))
				banco.execute("DELETE FROM funcionarios WHERE id = ?", (registro[0],))
			atualizar()

		atualizar()

	def editar_funcionario(self, registro, ao_salvar=None):
		janela = tk.Toplevel(self.janela)
		janela.title("Editar funcionário")
		janela.geometry("420x430")
		janela.resizable(False, False)
		janela.configure(bg="white")
		campos = {}
		valores = (("Nome", "nome", registro[1]), ("Cargo", "cargo", registro[2]),
				   ("Data de admissão", "admissao", registro[3]),
				   ("Salário / base", "salario", registro[4].replace("R$ ", "").replace(".", "").replace(",", ".")),
				   ("Comissão (%)", "comissao", registro[5].replace("%", "").replace(",", ".")))
		for rotulo, chave, valor in valores:
			tk.Label(janela, text=rotulo, bg="white", fg="#455a60", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=30, pady=(13, 2))
			entrada = tk.Entry(janela, font=("Segoe UI", 10), relief="solid", bd=1)
			entrada.insert(0, valor)
			entrada.pack(fill="x", padx=30, ipady=5)
			campos[chave] = entrada

		def salvar():
			try:
				nome = campos["nome"].get().strip()
				cargo = campos["cargo"].get().strip()
				admissao = campos["admissao"].get().strip()
				salario = float(campos["salario"].get().replace(",", "."))
				comissao = float(campos["comissao"].get().replace(",", "."))
				if not nome or salario < 0 or comissao < 0:
					raise ValueError
			except ValueError:
				messagebox.showerror("Dados inválidos", "Preencha os campos corretamente.", parent=janela)
				return
			with self.conectar() as banco:
				banco.execute("UPDATE funcionarios SET nome = ?, cargo = ?, admissao = ?, salario = ?, comissao = ? WHERE id = ?",
							  (nome, cargo, admissao, salario, comissao, registro[0]))
			janela.destroy()
			if ao_salvar:
				ao_salvar()

		tk.Button(janela, text="Salvar alterações", command=salvar, relief="flat", bg="#1f2d35", fg="white",
				  activebackground="#27545a", font=("Segoe UI", 10, "bold"), padx=20, pady=8).pack(pady=20)

	def abrir_cadastro_funcionario(self, _=None):
		nome = simpledialog.askstring("Novo funcionário", "Nome do funcionário:", parent=self.janela)
		if not nome or not nome.strip():
			return
		cargo = simpledialog.askstring("Novo funcionário", "Cargo:", parent=self.janela) or ""
		admissao = datetime.now().strftime("%Y-%m-%d")
		with self.conectar() as banco:
			banco.execute("INSERT INTO funcionarios (nome, cargo, admissao) VALUES (?, ?, ?)",
						  (nome.strip(), cargo.strip(), admissao))
		messagebox.showinfo("Funcionário cadastrado", "O funcionário foi cadastrado com sucesso.", parent=self.janela)

	def abrir_controle_ponto(self, _=None):
		for widget in self.area_principal.winfo_children():
			widget.destroy()
		janela = tk.Frame(self.area_principal, bg="#f1f5f7")
		janela.pack(fill="both", expand=True)
		self.criar_botao_voltar(janela, 30)
		tk.Label(janela, text="Controle de ponto", font=("Georgia", 25, "bold"),
				 foreground="#23343b", background="#f1f5f7").pack(anchor="w", padx=30, pady=(22, 2))
		tk.Label(janela, text="Registre a jornada e acompanhe as horas realizadas.", font=("Segoe UI", 10),
				 foreground="#62757a", background="#f1f5f7").pack(anchor="w", padx=32, pady=(0, 18))
		with self.conectar() as banco:
			funcionarios = banco.execute("SELECT id, nome, cargo FROM funcionarios WHERE ativo = 1 ORDER BY nome").fetchall()
		opcoes = {str(item["id"]) + " - " + item["nome"]: item for item in funcionarios}
		controles = tk.Frame(janela, bg="#ffffff", highlightbackground="#d6e2e0", highlightthickness=1)
		controles.pack(fill="x", padx=30, pady=(0, 14))
		tk.Label(controles, text="Funcionário", font=("Segoe UI", 9, "bold"), background="#ffffff",
				 foreground="#455a60").pack(side="left", padx=(16, 8), pady=16)
		funcionario = tk.StringVar()
		menu = ttk.Combobox(controles, textvariable=funcionario, values=tuple(opcoes), state="readonly", width=32)
		menu.pack(side="left", padx=(0, 12), ipady=4)
		status = tk.StringVar(value="Selecione um funcionário para começar.")
		tk.Label(controles, textvariable=status, font=("Segoe UI", 9), background="#ffffff",
				 foreground="#16827c").pack(side="left", padx=10)
		area = tk.Frame(janela, bg="#ffffff", highlightbackground="#d6e2e0", highlightthickness=1)
		area.pack(fill="both", expand=True, padx=30, pady=(0, 28))
		data_atual = datetime.now().strftime("%Y-%m-%d")
		registros = {"id": None, "entrada": None, "inicio_intervalo": None, "retorno_intervalo": None, "saida": None}
		jornada = tk.StringVar(value="Jornada realizada: -  |  Horas extras: -")

		def carregar_registro(_=None):
			selecionado = opcoes.get(funcionario.get())
			if not selecionado:
				return
			with self.conectar() as banco:
				registro = banco.execute("SELECT * FROM ponto_registros WHERE funcionario_id = ? AND data = ?",
						(selecionado["id"], data_atual)).fetchone()
			registros.update(dict(registro) if registro else {"id": None, "entrada": None, "inicio_intervalo": None, "retorno_intervalo": None, "saida": None})
			atualizar_status()

		def atualizar_status():
			marcos = (("Entrada", registros.get("entrada")), ("Intervalo", registros.get("inicio_intervalo")),
					  ("Retorno", registros.get("retorno_intervalo")), ("Saída", registros.get("saida")))
			status.set("  |  ".join(nome + ": " + (hora or "-") for nome, hora in marcos))
			if registros.get("entrada") and registros.get("saida"):
				inicio = datetime.strptime(registros["entrada"], "%H:%M")
				fim = datetime.strptime(registros["saida"], "%H:%M")
				duracao = fim - inicio
				if registros.get("inicio_intervalo") and registros.get("retorno_intervalo"):
					duracao -= datetime.strptime(registros["retorno_intervalo"], "%H:%M") - datetime.strptime(registros["inicio_intervalo"], "%H:%M")
				minutos = max(0, int(duracao.total_seconds() // 60))
				horas = minutos // 60
				resto = minutos % 60
				extra = max(0, minutos - 8 * 60)
				jornada.set("Jornada realizada: " + str(horas) + "h" + (str(resto).zfill(2) if resto else "") +
							"  |  Horas extras: " + str(extra // 60) + "h" + str(extra % 60).zfill(2))
			else:
				jornada.set("Jornada realizada: -  |  Horas extras: -")

		def registrar(tipo):
			selecionado = opcoes.get(funcionario.get())
			if not selecionado:
				messagebox.showwarning("Ponto", "Selecione um funcionário.", parent=janela)
				return
			hora = datetime.now().strftime("%H:%M")
			campo = {"entrada": "entrada", "intervalo": "inicio_intervalo", "retorno": "retorno_intervalo", "saida": "saida"}[tipo]
			if registros.get(campo):
				messagebox.showinfo("Ponto", "Este registro já foi marcado hoje.", parent=janela)
				return
			with self.conectar() as banco:
				if registros.get("id"):
					banco.execute("UPDATE ponto_registros SET " + campo + " = ? WHERE id = ?", (hora, registros["id"]))
				else:
					registro = banco.execute("INSERT INTO ponto_registros (funcionario_id, data, " + campo + ") VALUES (?, ?, ?)",
							(selecionado["id"], data_atual, hora))
					registros["id"] = registro.lastrowid
			registros[campo] = hora
			atualizar_status()

		menu.bind("<<ComboboxSelected>>", carregar_registro)
		botoes = tk.Frame(area, bg="#ffffff")
		botoes.pack(anchor="w", padx=22, pady=(24, 12))
		for texto, tipo, cor in (("Entrada", "entrada", "#16827c"), ("Início do intervalo", "intervalo", "#c48845"),
								("Retorno", "retorno", "#4c7a99"), ("Saída", "saida", "#bd4038")):
			tk.Button(botoes, text=texto, command=lambda valor=tipo: registrar(valor), relief="flat", bg=cor,
					fg="white", activebackground=cor, font=("Segoe UI", 10, "bold"), padx=14, pady=9).pack(side="left", padx=(0, 8))
		tk.Label(area, text="Jornada prevista: 8h", font=("Segoe UI", 12, "bold"), background="#ffffff",
				 foreground="#23343b").pack(anchor="w", padx=22, pady=(22, 4))
		tk.Label(area, textvariable=jornada, font=("Segoe UI", 11, "bold"), background="#ffffff",
				 foreground="#16827c").pack(anchor="w", padx=22)

	def abrir_controle_estoque(self):
		for widget in self.area_principal.winfo_children():
			widget.destroy()
		self.criar_botao_voltar(self.area_principal, 30)
		self.titulo_insumos = tk.Label(self.area_principal, text="Controle de estoque", font=("Georgia", 25, "bold"),
							  fg="#23343b", bg="#f1f5f7")
		self.titulo_insumos.pack(anchor="w", padx=30, pady=(25, 18))
		painel = tk.Frame(self.area_principal, bg="#ffffff", relief="raised", bd=2,
					  highlightbackground="#c2d5d2", highlightthickness=1)
		painel.pack(fill="both", expand=True, padx=30, pady=(0, 28))
		ferramentas = tk.Frame(painel, bg="#ffffff")
		ferramentas.pack(fill="x", padx=18, pady=16)
		tk.Label(ferramentas, text="Estabelecimento:", font=("Segoe UI", 10, "bold"),
				 fg="#455a60", bg="#ffffff").pack(side="left")
		menu_estabelecimento = ttk.Combobox(ferramentas, textvariable=self.estabelecimento,
				 values=("Churrascaria", "Mercado", "Sorveteria", "Mercearia", "Hamburgaria", "Pizzaria"),
				 state="readonly", width=18)
		menu_estabelecimento.pack(side="left", padx=(8, 18), ipady=4)
		menu_estabelecimento.bind("<<ComboboxSelected>>", lambda _: self.trocar_estabelecimento())
		self.titulo_insumos = tk.Label(ferramentas, text="Insumos da " + self.estabelecimento.get(),
				font=("Segoe UI", 14, "bold"), fg="#23343b", bg="#ffffff")
		self.titulo_insumos.pack(side="left")
		tk.Button(ferramentas, text="+  Cadastrar produto",
				command=lambda: self.executar_com_permissao("gerente", self.abrir_cadastro),
				relief="flat", bg="#d45b45", fg="white", activebackground="#b84435",
				activeforeground="white", font=("Segoe UI", 9, "bold"), padx=12, pady=7).pack(side="left", padx=(18, 0))
		tk.Button(ferramentas, text="Baixar PDF", command=lambda: self.baixar_pdf_funcao("Estoque", "Produtos", "Inventário atual"),
				relief="flat", bg="#4c7a99", fg="white", activebackground="#355d78",
				font=("Segoe UI", 9, "bold"), padx=12, pady=7).pack(side="left", padx=(8, 0))
		self.pesquisa = tk.StringVar()
		self.pesquisa.trace_add("write", lambda *_: self.atualizar_tabela())
		tk.Entry(ferramentas, textvariable=self.pesquisa, width=30, relief="solid", bd=1,
				 font=("Segoe UI", 10)).pack(side="right", ipady=6, padx=(8, 0))
		tk.Label(ferramentas, text="Pesquisar:", font=("Segoe UI", 10), fg="#62757a",
				 bg="#ffffff").pack(side="right")
		self.filtro_categoria = tk.StringVar(value="Todas as categorias")
		self.combo_categoria = ttk.Combobox(ferramentas, textvariable=self.filtro_categoria,
				 values=("Todas as categorias",), state="readonly", width=20)
		self.combo_categoria.pack(side="right", padx=(18, 8), ipady=4)
		self.combo_categoria.bind("<<ComboboxSelected>>", lambda _: self.atualizar_tabela())
		tk.Button(ferramentas, text="Ver estoque baixo", command=self.alternar_filtro_baixo,
				relief="flat", bg="#fbe5df", fg="#b84435", font=("Segoe UI", 9, "bold"),
				padx=8, pady=7).pack(side="left", padx=(18, 0))
		self.mostrar_apenas_baixo = False

		area_tabela = tk.Frame(painel, bg="#ffffff")
		area_tabela.pack(fill="both", expand=True, padx=18, pady=(0, 15))
		colunas = ("id", "nome", "categoria", "unidade", "quantidade", "minimo", "custo", "fornecedor", "situacao")
		self.tabela = ttk.Treeview(area_tabela, columns=colunas, show="headings", selectmode="browse")
		nomes = {"id": "ID", "nome": "INSUMO", "categoria": "CATEGORIA", "unidade": "UN.",
				 "quantidade": "QTD.", "minimo": "MINIMO", "custo": "CUSTO", "fornecedor": "FORNECEDOR", "situacao": "SITUACAO"}
		larguras = {"id": 40, "nome": 170, "categoria": 115, "unidade": 65, "quantidade": 70,
				 "minimo": 70, "custo": 90, "fornecedor": 150, "situacao": 115}
		for coluna in colunas:
			self.tabela.heading(coluna, text=nomes[coluna])
			self.tabela.column(coluna, width=larguras[coluna], anchor="w")
		self.tabela.tag_configure("baixo", foreground="#c94b43")
		self.tabela.bind("<Double-1>", lambda _: self.editar_insumo())
		self.menu_insumo = tk.Menu(self.janela, tearoff=False)
		self.menu_insumo.add_command(label="Excluir insumo selecionado", command=self.excluir_insumo)
		self.tabela.bind("<Button-3>", self.mostrar_menu_insumo)
		self.tabela.pack(side="left", fill="both", expand=True)
		rolagem = ttk.Scrollbar(area_tabela, orient="vertical", command=self.tabela.yview)
		rolagem.pack(side="right", fill="y")
		self.tabela.configure(yscrollcommand=rolagem.set)
		acoes = tk.Frame(painel, bg="#ffffff")
		acoes.pack(fill="x", padx=18, pady=(0, 18))
		for texto, comando, cor in [("Editar selecionado", self.editar_insumo, "#4c7a99"),
									("Entrada / Saída", self.abrir_movimentacao, "#16827c"),
									("Duplicar insumo", self.duplicar_insumo, "#c48845"),
									("Excluir selecionado", self.excluir_insumo, "#bd4038")]:
			tk.Button(acoes, text=texto, command=comando, relief="flat", bg=cor, fg="white",
					  activebackground=cor, activeforeground="white", font=("Segoe UI", 9, "bold"),
					  padx=12, pady=8).pack(side="left", padx=(0, 8))
		self.atualizar_tela()

	def abrir_vendas(self):
		for widget in self.area_principal.winfo_children():
			widget.destroy()
		janela = tk.Frame(self.area_principal, bg="#f1f5f7")
		janela.pack(fill="both", expand=True)
		janela.configure(bg="#f1f5f7")
		self.criar_botao_voltar(janela, 26)
		tk.Label(janela, text="Vendas", font=("Georgia", 22, "bold"),
				 foreground="#1f2d35", background="#f1f5f7").pack(anchor="w", padx=26, pady=(22, 2))
		tk.Label(janela, text="Registre uma venda e atualize o estoque automaticamente.", font=("Segoe UI", 10),
				 foreground="#62757a", background="#eef3f2").pack(anchor="w", padx=28, pady=(0, 16))
		tk.Button(janela, text="Baixar PDF", command=lambda: self.baixar_pdf_funcao("Vendas", "PDV", "Resumo de vendas"),
				relief="flat", bg="#4c7a99", fg="white", activebackground="#355d78",
				font=("Segoe UI", 9, "bold"), padx=12, pady=7).pack(anchor="ne", padx=26, pady=(0, 10))
		controles = tk.Frame(janela, bg="white", highlightbackground="#d6e2e0", highlightthickness=1)
		controles.pack(fill="x", padx=26, pady=(0, 14))
		tk.Label(controles, text="Código do produto", background="white", foreground="#455a60",
				 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(15, 6), pady=15)
		codigo_produto = tk.StringVar()
		entrada_codigo = tk.Entry(controles, textvariable=codigo_produto, width=20, font=("Segoe UI", 10), relief="solid", bd=1)
		entrada_codigo.pack(side="left", padx=(0, 12), ipady=5)
		produto_selecionado = tk.StringVar(value="Digite o código e pressione Enter")
		valor_selecionado = tk.StringVar(value="")
		info_produto = tk.Frame(controles, bg="white")
		info_produto.pack(side="left", padx=(0, 15))
		tk.Label(info_produto, textvariable=produto_selecionado, background="white", foreground="#23343b",
				 font=("Segoe UI", 9, "bold")).pack(anchor="w")
		tk.Label(info_produto, textvariable=valor_selecionado, background="white", foreground="#16827c",
				 font=("Segoe UI", 9)).pack(anchor="w")
		tk.Label(controles, text="Quantidade", background="white", foreground="#455a60",
				 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
		quantidade = tk.Entry(controles, width=10, font=("Segoe UI", 10), relief="solid", bd=1)
		quantidade.insert(0, "1")
		quantidade.pack(side="left", ipady=5)

		area = tk.Frame(janela, bg="white", highlightbackground="#d6e2e0", highlightthickness=1)
		area.pack(fill="both", expand=True, padx=26, pady=(0, 16))
		tabela = ttk.Treeview(area, columns=("produto", "quantidade", "preco", "subtotal"), show="headings")
		for coluna, titulo, largura in (("produto", "PRODUTO", 360), ("quantidade", "QUANTIDADE", 130),
										("preco", "PREÇO UNITÁRIO", 150), ("subtotal", "SUBTOTAL", 150)):
			tabela.heading(coluna, text=titulo)
			tabela.column(coluna, width=largura, anchor="w")
		tabela.pack(side="left", fill="both", expand=True, padx=15, pady=15)
		rolagem = ttk.Scrollbar(area, orient="vertical", command=tabela.yview)
		rolagem.pack(side="right", fill="y", pady=15)
		tabela.configure(yscrollcommand=rolagem.set)
		itens = []
		total = tk.StringVar(value="Total: R$ 0,00")
		registro_codigo = {"valor": None}

		def localizar_produto(_=None):
			codigo = codigo_produto.get().strip()
			with self.conectar() as banco:
				registro = banco.execute("SELECT id, nome, unidade, quantidade, custo FROM insumos WHERE codigo_barras = ? AND estabelecimento = ? AND origem = 'estoque'",
						(codigo, self.estabelecimento.get())).fetchone()
			registro_codigo["valor"] = registro
			if registro:
				produto_selecionado.set(registro["nome"])
				valor_selecionado.set("Valor: " + self.formatar_moeda(registro["custo"]))
				quantidade.focus_set()
			else:
				produto_selecionado.set("Produto não encontrado")
				valor_selecionado.set("")

		def atualizar_carrinho():
			for item in tabela.get_children():
				tabela.delete(item)
			valor_total = 0
			for item in itens:
				subtotal = item["quantidade"] * item["preco"]
				valor_total += subtotal
				tabela.insert("", "end", values=(item["nome"], self.formatar_numero(item["quantidade"]),
					self.formatar_moeda(item["preco"]), self.formatar_moeda(subtotal)))
			total.set("Total: " + self.formatar_moeda(valor_total))

		def adicionar_item():
			registro = registro_codigo["valor"]
			try:
				valor_quantidade = float(quantidade.get().replace(",", "."))
				if not registro or valor_quantidade <= 0:
					raise ValueError
			except ValueError:
				messagebox.showerror("Item inválido", "Selecione um produto e informe uma quantidade válida.", parent=janela)
				return
			itens.append({"id": registro["id"], "nome": registro["nome"], "quantidade": valor_quantidade,
				"preco": registro["custo"], "unidade": registro["unidade"]})
			codigo_produto.set("")
			registro_codigo["valor"] = None
			produto_selecionado.set("Digite o código e pressione Enter")
			valor_selecionado.set("")
			atualizar_carrinho()

		def finalizar_venda():
			if not itens:
				messagebox.showwarning("Venda vazia", "Adicione pelo menos um produto à venda.", parent=janela)
				return
			valor_total = sum(item["quantidade"] * item["preco"] for item in itens)
			pagamento = tk.Toplevel(janela)
			pagamento.title("Forma de pagamento")
			pagamento.geometry("360x260")
			pagamento.resizable(False, False)
			pagamento.configure(bg="white")
			tk.Label(pagamento, text="Como foi o pagamento?", font=("Georgia", 16, "bold"),
					 foreground="#1f2d35", background="white").pack(pady=(24, 8))
			tk.Label(pagamento, text="Escolha uma opção e pressione Enter", font=("Segoe UI", 9),
					 foreground="#62757a", background="white").pack(pady=(0, 12))
			forma = tk.StringVar(value="Dinheiro")
			menu_pagamento = ttk.Combobox(pagamento, textvariable=forma,
					values=("Crédito", "Débito", "Pix", "Dinheiro"), state="readonly", width=22)
			menu_pagamento.pack(ipady=5)

			def concluir_pagamento(_=None):
				pagamento.destroy()
				try:
					with self.conectar() as banco:
						for item in itens:
							estoque = banco.execute("SELECT quantidade FROM insumos WHERE id = ?", (item["id"],)).fetchone()
							if not estoque or item["quantidade"] > estoque["quantidade"]:
								raise ValueError("Estoque insuficiente para " + item["nome"] + ".")
						venda = banco.execute("INSERT INTO vendas (estabelecimento, usuario, total, forma_pagamento) VALUES (?, ?, ?, ?)",
							(self.estabelecimento.get(), self.usuario_logado, valor_total, forma.get()))
						venda_id = venda.lastrowid
						for item in itens:
							subtotal = item["quantidade"] * item["preco"]
							banco.execute("INSERT INTO venda_itens (venda_id, insumo_id, nome, quantidade, preco_unitario, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
								(venda_id, item["id"], item["nome"], item["quantidade"], item["preco"], subtotal))
							banco.execute("UPDATE insumos SET quantidade = quantidade - ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?",
								(item["quantidade"], item["id"]))
							banco.execute("INSERT INTO movimentacoes (insumo_id, tipo, quantidade) VALUES (?, 'Saida', ?)",
								(item["id"], item["quantidade"]))
					comprovante = self.gerar_comprovante_venda(venda_id, forma.get(), valor_total, itens)
					banco.execute("UPDATE vendas SET comprovante = ? WHERE id = ?", (comprovante, venda_id))
				except (sqlite3.Error, ValueError) as erro:
					messagebox.showerror("Venda não concluída", str(erro), parent=janela)
					return
				janela.destroy()
				self.mostrar_feedback("Venda salva com sucesso")
				self.abrir_vendas()
				self.mostrar_comprovante_venda(comprovante, venda_id, forma.get(), valor_total, itens)

			tk.Button(pagamento, text="Confirmar pagamento", command=concluir_pagamento, relief="flat",
					 bg="#16827c", fg="white", activebackground="#12645e",
					 font=("Segoe UI", 10, "bold"), padx=15, pady=8).pack(pady=18)
			menu_pagamento.focus_set()
			menu_pagamento.bind("<Return>", concluir_pagamento)
			pagamento.transient(janela)
			pagamento.grab_set()

		tk.Button(controles, text="Adicionar item", command=adicionar_item, relief="flat", bg="#c48845", fg="white",
				 activebackground="#9f6638", font=("Segoe UI", 9, "bold"), padx=12, pady=7).pack(side="left", padx=12)
		tk.Button(controles, text="Leitor de código de barras", command=self.abrir_leitor_codigo, relief="flat",
				 bg="#4c7a99", fg="white", activebackground="#3a617a", font=("Segoe UI", 9, "bold"),
				 padx=12, pady=7).pack(side="left", padx=(0, 12))
		tk.Button(controles, text="Cadastrar produto", command=lambda: self.executar_com_permissao("gerente", lambda: self.abrir_cadastro(modo_produto=True, modulo="vendas")), relief="flat",
				 bg="#d45b45", fg="white", activebackground="#b84435", font=("Segoe UI", 9, "bold"),
				 padx=12, pady=7).pack(side="left", padx=(0, 12))
		rodape = tk.Frame(janela, bg="#eef3f2")
		rodape.pack(fill="x", padx=26, pady=(0, 20))
		tk.Label(rodape, textvariable=total, font=("Segoe UI", 14, "bold"), foreground="#16827c",
				 background="#eef3f2").pack(side="left")
		tk.Button(rodape, text="Finalizar venda", command=finalizar_venda, relief="flat", bg="#16827c", fg="white",
				 activebackground="#12645e", font=("Segoe UI", 10, "bold"), padx=18, pady=9).pack(side="right")
		tk.Button(rodape, text="Vendas concluídas", command=self.abrir_vendas_concluidas, relief="flat", bg="#4c7a99", fg="white",
				 activebackground="#3a617a", font=("Segoe UI", 9, "bold"), padx=12, pady=8).pack(side="right", padx=(0, 8))

		def confirmar_codigo(_=None):
			localizar_produto()
			if registro_codigo["valor"]:
				adicionar_item()
				finalizar_venda()

		entrada_codigo.bind("<Return>", confirmar_codigo)
		entrada_codigo.focus_set()

	def gerar_comprovante_venda(self, venda_id, forma_pagamento, total, itens):
		momento = datetime.now()
		nome_arquivo = "comprovante_venda_" + str(venda_id) + "_" + momento.strftime("%Y%m%d_%H%M%S") + ".pdf"
		caminho = os.path.join(PASTA_SISTEMA, nome_arquivo)
		linhas = [NOME_SISTEMA + " - COMPROVANTE DE VENDA", "Venda: " + str(venda_id),
			"Data: " + momento.strftime("%d/%m/%Y %H:%M"), "", "PRODUTO                         QTD.       VALOR"]
		for item in itens:
			linhas.append("{:<30} {:>6}   {:>12}".format(item["nome"][:30], self.formatar_numero(item["quantidade"]),
				self.formatar_moeda(item["quantidade"] * item["preco"])))
		linhas.extend(["", "TOTAL: " + self.formatar_moeda(total), "FORMA DE PAGAMENTO: " + forma_pagamento, "Obrigado pela preferência!"])
		objetos = {1: b"<< /Type /Catalog /Pages 2 0 R >>", 3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>"}
		conteudo = ["BT", "/F1 10 Tf", "40 780 Td", "14 TL"]
		for linha in linhas:
			texto = linha.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
			conteudo.append("(" + texto + ") Tj T*")
		conteudo.append("ET")
		bytes_conteudo = "\n".join(conteudo).encode("latin-1", "replace")
		objetos[4] = b"<< /Length " + str(len(bytes_conteudo)).encode() + b" >>\nstream\n" + bytes_conteudo + b"\nendstream"
		objetos[2] = b"<< /Type /Pages /Kids [5 0 R] /Count 1 >>"
		objetos[5] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R >>"
		pdf = bytearray(b"%PDF-1.4\n")
		offsets = [0] * 6
		for numero in range(1, 6):
			offsets[numero] = len(pdf)
			pdf.extend(str(numero).encode() + b" 0 obj\n" + objetos[numero] + b"\nendobj\n")
		xref = len(pdf)
		pdf.extend(b"xref\n0 6\n0000000000 65535 f \n")
		for numero in range(1, 6):
			pdf.extend(("{:010d} 00000 n \n".format(offsets[numero])).encode())
		pdf.extend(("trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{}\n%%EOF".format(xref)).encode())
		with open(caminho, "wb") as arquivo:
			arquivo.write(pdf)
		return caminho

	def mostrar_comprovante_venda(self, caminho, venda_id, forma_pagamento, total, itens):
		janela = tk.Toplevel(self.janela)
		janela.title("Comprovante de venda")
		janela.geometry("560x520")
		janela.resizable(False, False)
		janela.configure(bg="white")
		tk.Label(janela, text="Venda concluída", font=("Georgia", 21, "bold"),
				 foreground="#16827c", background="white").pack(pady=(24, 3))
		tk.Label(janela, text="Comprovante de venda", font=("Segoe UI", 10),
				 foreground="#62757a", background="white").pack(pady=(0, 16))
		area = tk.Text(janela, height=15, width=58, state="normal", font=("Consolas", 10),
				 bg="#f7faf9", fg="#23343b", relief="solid", bd=1, padx=12, pady=10)
		area.pack(fill="both", expand=True, padx=28)
		area.insert(tk.END, NOME_SISTEMA + " - COMPROVANTE DE VENDA\n")
		area.insert(tk.END, "Venda: " + str(venda_id) + "\n")
		area.insert(tk.END, "-" * 52 + "\n")
		for item in itens:
			area.insert(tk.END, item["nome"] + "\n")
			area.insert(tk.END, "  Quantidade: " + self.formatar_numero(item["quantidade"]) +
					" | Valor: " + self.formatar_moeda(item["quantidade"] * item["preco"]) + "\n")
		area.insert(tk.END, "-" * 52 + "\n")
		area.insert(tk.END, "TOTAL: " + self.formatar_moeda(total) + "\n")
		area.insert(tk.END, "PAGAMENTO: " + forma_pagamento + "\n")
		area.insert(tk.END, "\nArquivo PDF: " + os.path.basename(caminho))
		area.configure(state="disabled")

		def salvar_pdf():
			destino = filedialog.asksaveasfilename(parent=janela, title="Salvar comprovante de venda",
					defaultextension=".pdf", initialfile=os.path.basename(caminho),
					filetypes=(("Arquivo PDF", "*.pdf"), ("Todos os arquivos", "*.*")))
			if destino:
				shutil.copyfile(caminho, destino)
				messagebox.showinfo("PDF salvo", "Comprovante salvo em:\n" + destino, parent=janela)

		def abrir_pdf():
			try:
				os.startfile(caminho)
			except OSError as erro:
				messagebox.showerror("PDF indisponível", "Não foi possível abrir o PDF:\n" + str(erro), parent=janela)

		botoes = tk.Frame(janela, bg="white")
		botoes.pack(fill="x", padx=28, pady=18)
		tk.Button(botoes, text="Salvar PDF", command=salvar_pdf, relief="flat", bg="#16827c", fg="white",
				 activebackground="#12645e", font=("Segoe UI", 10, "bold"), padx=18, pady=9).pack(side="right")
		tk.Button(botoes, text="Abrir PDF", command=abrir_pdf, relief="flat", bg="#4c7a99", fg="white",
				 activebackground="#3a617a", font=("Segoe UI", 10, "bold"), padx=18, pady=9).pack(side="right", padx=(0, 8))

	def abrir_vendas_concluidas(self):
		janela = tk.Toplevel(self.janela)
		janela.title("Vendas concluidas - " + NOME_SISTEMA)
		janela.geometry("850x480")
		janela.configure(bg="#eef3f2")
		tk.Label(janela, text="Vendas concluídas", font=("Georgia", 20, "bold"), foreground="#1f2d35", background="#eef3f2").pack(anchor="w", padx=24, pady=(20, 12))
		area = tk.Frame(janela, bg="white")
		area.pack(fill="both", expand=True, padx=24, pady=(0, 18))
		tabela = ttk.Treeview(area, columns=("id", "data", "total", "pagamento", "comprovante"), show="headings")
		for coluna, titulo, largura in (("id", "ID", 55), ("data", "DATA", 170), ("total", "TOTAL", 130), ("pagamento", "PAGAMENTO", 130), ("comprovante", "COMPROVANTE", 260)):
			tabela.heading(coluna, text=titulo)
			tabela.column(coluna, width=largura, anchor="w")
		tabela.pack(fill="both", expand=True, padx=14, pady=14)
		with self.conectar() as banco:
			vendas = banco.execute("SELECT id, data, total, forma_pagamento, comprovante FROM vendas WHERE estabelecimento = ? ORDER BY id DESC",
					(self.estabelecimento.get(),)).fetchall()
		for venda in vendas:
			tabela.insert("", "end", values=(venda["id"], venda["data"], self.formatar_moeda(venda["total"]), venda["forma_pagamento"], venda["comprovante"]))

		def baixar_comprovante():
			selecao = tabela.selection()
			if not selecao:
				messagebox.showwarning("Nenhuma venda", "Selecione uma venda concluída.", parent=janela)
				return
			valores = tabela.item(selecao[0], "values")
			origem = valores[4]
			if not origem or not os.path.exists(origem):
				messagebox.showerror("Comprovante indisponível", "O PDF desta venda não foi encontrado.", parent=janela)
				return
			destino = filedialog.asksaveasfilename(parent=janela, title="Baixar comprovante", defaultextension=".pdf",
					initialfile=os.path.basename(origem), filetypes=(("Arquivo PDF", "*.pdf"), ("Todos os arquivos", "*.*")))
			if destino:
				shutil.copyfile(origem, destino)
				messagebox.showinfo("Download concluído", "Comprovante salvo em:\n" + destino, parent=janela)

		tk.Button(janela, text="Baixar PDF selecionado", command=baixar_comprovante, relief="flat", bg="#16827c", fg="white",
				 activebackground="#12645e", font=("Segoe UI", 10, "bold"), padx=16, pady=8).pack(pady=(0, 18))

	def abrir_pedidos_mesa(self):
		for widget in self.area_principal.winfo_children():
			widget.destroy()
		janela = tk.Frame(self.area_principal, bg="#f1f5f7")
		janela.pack(fill="both", expand=True)
		janela.configure(bg="#f1f5f7")
		self.criar_botao_voltar(janela, 26)
		tk.Label(janela, text="Pedidos de mesa", font=("Georgia", 22, "bold"),
				 foreground="#1f2d35", background="#f1f5f7").pack(anchor="w", padx=26, pady=(22, 2))
		tk.Label(janela, text="Abra pedidos, acompanhe as mesas e feche quando o consumo for pago.", font=("Segoe UI", 10),
				 foreground="#62757a", background="#eef3f2").pack(anchor="w", padx=28, pady=(0, 16))
		tk.Button(janela, text="Baixar PDF", command=lambda: self.baixar_pdf_funcao("Mesas e pedidos", "Pedidos", "Resumo das mesas"),
				relief="flat", bg="#4c7a99", fg="white", activebackground="#355d78",
				font=("Segoe UI", 9, "bold"), padx=12, pady=7).pack(anchor="ne", padx=26, pady=(0, 10))
		with self.conectar() as banco:
			registros = banco.execute("SELECT id, nome, unidade, custo FROM insumos WHERE estabelecimento = ? ORDER BY nome",
							(self.estabelecimento.get(),)).fetchall()
		opcoes = {str(registro["id"]) + " - " + registro["nome"]: registro for registro in registros}
		controles = tk.Frame(janela, bg="white", highlightbackground="#d6e2e0", highlightthickness=1)
		controles.pack(fill="x", padx=26, pady=(0, 14))
		tk.Label(controles, text="Mesa", background="white", foreground="#455a60", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(15, 6), pady=15)
		mesa = tk.Entry(controles, width=8, font=("Segoe UI", 10), relief="solid", bd=1)
		mesa.pack(side="left", padx=(0, 18), ipady=5)
		tk.Label(controles, text="Produto", background="white", foreground="#455a60", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
		produto = tk.StringVar()
		menu_produto = ttk.Combobox(controles, textvariable=produto, values=tuple(opcoes), state="readonly", width=32)
		menu_produto.pack(side="left", padx=(0, 12), ipady=4)

		def atualizar_opcoes_produtos():
			opcoes.clear()
			with self.conectar() as banco:
				registros_atualizados = banco.execute(
					"SELECT id, nome, unidade, custo FROM insumos WHERE estabelecimento = ? ORDER BY nome",
					(self.estabelecimento.get(),)).fetchall()
			for registro in registros_atualizados:
				opcoes[str(registro["id"]) + " - " + registro["nome"]] = registro
			menu_produto["values"] = tuple(opcoes)

		quantidade = tk.Entry(controles, width=8, font=("Segoe UI", 10), relief="solid", bd=1)
		quantidade.insert(0, "1")
		quantidade.pack(side="left", padx=(0, 10), ipady=5)

		area_itens = tk.Frame(janela, bg="white", highlightbackground="#d6e2e0", highlightthickness=1)
		area_itens.pack(fill="both", expand=True, padx=26, pady=(0, 14))
		tabela_itens = ttk.Treeview(area_itens, columns=("produto", "quantidade", "preco", "subtotal"), show="headings")
		for coluna, titulo, largura in (("produto", "PRODUTO", 340), ("quantidade", "QUANTIDADE", 130),
										("preco", "PREÇO UNITÁRIO", 150), ("subtotal", "SUBTOTAL", 150)):
			tabela_itens.heading(coluna, text=titulo)
			tabela_itens.column(coluna, width=largura, anchor="w")
		tabela_itens.pack(fill="both", expand=True, padx=15, pady=15)
		itens = []
		total = tk.StringVar(value="Total do novo pedido: R$ 0,00")

		def atualizar_itens():
			for item in tabela_itens.get_children():
				tabela_itens.delete(item)
			valor_total = 0
			for item in itens:
				subtotal = item["quantidade"] * item["preco"]
				valor_total += subtotal
				tabela_itens.insert("", "end", values=(item["nome"], self.formatar_numero(item["quantidade"]),
					self.formatar_moeda(item["preco"]), self.formatar_moeda(subtotal)))
			total.set("Total do novo pedido: " + self.formatar_moeda(valor_total))

		def adicionar_item():
			registro = opcoes.get(produto.get())
			try:
				valor_quantidade = float(quantidade.get().replace(",", "."))
				if not registro or not mesa.get().strip() or valor_quantidade <= 0:
					raise ValueError
			except ValueError:
				messagebox.showerror("Item inválido", "Informe a mesa, selecione o produto e use uma quantidade válida.", parent=janela)
				return
			itens.append({"id": registro["id"], "nome": registro["nome"], "quantidade": valor_quantidade, "preco": registro["custo"]})
			atualizar_itens()

		area_pedidos = tk.Frame(janela, bg="white", highlightbackground="#d6e2e0", highlightthickness=1)
		area_pedidos.pack(fill="x", padx=26, pady=(0, 14))
		tk.Label(area_pedidos, text="Pedidos abertos", font=("Segoe UI", 11, "bold"), foreground="#1f2d35", background="white").pack(anchor="w", padx=15, pady=(10, 4))
		tabela_pedidos = ttk.Treeview(area_pedidos, columns=("id", "mesa", "total", "aberto"), show="headings", height=4)
		for coluna, titulo, largura in (("id", "ID", 55), ("mesa", "MESA", 130), ("total", "TOTAL", 150), ("aberto", "ABERTO EM", 200)):
			tabela_pedidos.heading(coluna, text=titulo)
			tabela_pedidos.column(coluna, width=largura, anchor="w")
		tabela_pedidos.pack(fill="x", padx=15, pady=(0, 10))

		def atualizar_pedidos():
			for item in tabela_pedidos.get_children():
				tabela_pedidos.delete(item)
			with self.conectar() as banco:
				abertos = banco.execute("SELECT id, mesa, total, aberto_em FROM pedidos_mesa WHERE estabelecimento = ? AND status = 'aberto' ORDER BY id DESC",
						(self.estabelecimento.get(),)).fetchall()
			for pedido in abertos:
				tabela_pedidos.insert("", "end", values=(pedido["id"], pedido["mesa"], self.formatar_moeda(pedido["total"]), pedido["aberto_em"]))

		def salvar_pedido():
			if not mesa.get().strip() or not itens:
				messagebox.showwarning("Pedido incompleto", "Informe a mesa e adicione pelo menos um item.", parent=janela)
				return
			valor_total = sum(item["quantidade"] * item["preco"] for item in itens)
			with self.conectar() as banco:
				pedido = banco.execute("INSERT INTO pedidos_mesa (mesa, estabelecimento, usuario, total) VALUES (?, ?, ?, ?)",
						(mesa.get().strip(), self.estabelecimento.get(), self.usuario_logado, valor_total))
				pedido_id = pedido.lastrowid
				for item in itens:
					banco.execute("INSERT INTO pedido_mesa_itens (pedido_id, insumo_id, nome, quantidade, preco_unitario, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
						(pedido_id, item["id"], item["nome"], item["quantidade"], item["preco"], item["quantidade"] * item["preco"]))
			itens.clear()
			mesa.delete(0, tk.END)
			produto.set("")
			atualizar_itens()
			atualizar_pedidos()
			self.mostrar_feedback("Pedido salvo com sucesso")
			messagebox.showinfo("Pedido aberto", "Pedido da mesa salvo com sucesso.", parent=janela)

		def fechar_pedido():
			selecao = tabela_pedidos.selection()
			if not selecao:
				messagebox.showwarning("Nenhum pedido", "Selecione um pedido aberto para fechar.", parent=janela)
				return
			pedido_id = tabela_pedidos.item(selecao[0], "values")[0]
			try:
				with self.conectar() as banco:
					pedido_itens = banco.execute("SELECT * FROM pedido_mesa_itens WHERE pedido_id = ?", (pedido_id,)).fetchall()
					for item in pedido_itens:
						estoque = banco.execute("SELECT quantidade FROM insumos WHERE id = ?", (item["insumo_id"],)).fetchone()
						if not estoque or item["quantidade"] > estoque["quantidade"]:
							raise ValueError("Estoque insuficiente para " + item["nome"] + ".")
					pedido = banco.execute("SELECT estabelecimento, total FROM pedidos_mesa WHERE id = ?", (pedido_id,)).fetchone()
					venda = banco.execute("INSERT INTO vendas (estabelecimento, usuario, total) VALUES (?, ?, ?)",
						(pedido["estabelecimento"], self.usuario_logado, pedido["total"]))
					for item in pedido_itens:
						banco.execute("UPDATE insumos SET quantidade = quantidade - ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?",
							(item["quantidade"], item["insumo_id"]))
						banco.execute("INSERT INTO movimentacoes (insumo_id, tipo, quantidade) VALUES (?, 'Saida', ?)",
							(item["insumo_id"], item["quantidade"]))
						banco.execute("INSERT INTO venda_itens (venda_id, insumo_id, nome, quantidade, preco_unitario, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
							(venda.lastrowid, item["insumo_id"], item["nome"], item["quantidade"], item["preco_unitario"], item["subtotal"]))
					banco.execute("UPDATE pedidos_mesa SET status = 'fechado', fechado_em = CURRENT_TIMESTAMP WHERE id = ?", (pedido_id,))
			except (sqlite3.Error, ValueError) as erro:
				messagebox.showerror("Pedido não fechado", str(erro), parent=janela)
				return
			atualizar_pedidos()
			self.atualizar_tela()
			messagebox.showinfo("Pedido fechado", "Pedido da mesa finalizado com sucesso.", parent=janela)

		tk.Button(controles, text="Adicionar item", command=adicionar_item, relief="flat", bg="#c48845", fg="white",
				 activebackground="#9f6638", font=("Segoe UI", 9, "bold"), padx=12, pady=7).pack(side="left", padx=10)
		tk.Button(controles, text="Cadastrar item", command=lambda: self.executar_com_permissao(
				"gerente", lambda: self.abrir_cadastro(modo_produto=True, ao_salvar=atualizar_opcoes_produtos, modulo="pedidos")),
				 relief="flat", bg="#d45b45", fg="white", activebackground="#b84435",
				 font=("Segoe UI", 9, "bold"), padx=12, pady=7).pack(side="left", padx=(0, 10))
		rodape = tk.Frame(janela, bg="#eef3f2")
		rodape.pack(fill="x", padx=26, pady=(0, 18))
		tk.Label(rodape, textvariable=total, font=("Segoe UI", 12, "bold"), foreground="#16827c", background="#eef3f2").pack(side="left")
		tk.Button(rodape, text="Salvar pedido", command=salvar_pedido, relief="flat", bg="#c48845", fg="white",
				 activebackground="#9f6638", font=("Segoe UI", 10, "bold"), padx=15, pady=8).pack(side="right", padx=(8, 0))
		tk.Button(rodape, text="Fechar pedido selecionado", command=fechar_pedido, relief="flat", bg="#16827c", fg="white",
				 activebackground="#12645e", font=("Segoe UI", 10, "bold"), padx=15, pady=8).pack(side="right")
		atualizar_pedidos()

	def criar_cartao_modulo(self, pai, titulo, descricao, comando, cor):
		sombra = tk.Frame(pai, bg="#CBD5E1", height=236, cursor="hand2")
		sombra.pack(side="left", fill="both", expand=True, padx=7, pady=(0, 4))
		sombra.pack_propagate(False)
		cartao = tk.Frame(sombra, bg=cor, relief="flat", bd=0,
					  highlightbackground="#c2d5d2", highlightthickness=2, cursor="hand2",
					  height=232)
		cartao.pack(fill="both", expand=True, padx=(0, 2), pady=(0, 2))
		cartao.pack_propagate(False)
		faixa = tk.Frame(cartao, bg="#ffffff", height=4, cursor="hand2")
		faixa.pack(fill="x", padx=24, pady=(16, 0))
		conteudo = tk.Frame(cartao, bg=cor, cursor="hand2")
		conteudo.pack(fill="both", expand=True, padx=7, pady=(0, 7))
		tipo_icone = "estoque" if "ESTOQUE" in titulo else ("vendas" if "VENDAS" in titulo else "pedidos")
		icone = tk.Canvas(conteudo, width=142, height=92, bg=cor, highlightthickness=0, cursor="hand2")
		desenhar_icone_cartao(icone, tipo_icone, cor)
		icone.pack(pady=(8, 0))
		rotulo = tk.Label(conteudo, text=titulo, font=("Segoe UI", 15, "bold"),
						 fg="white", bg=cor, justify="center", cursor="hand2")
		rotulo.pack(pady=(4, 3))
		detalhe = tk.Label(conteudo, text=descricao, font=("Segoe UI", 9),
						 fg="#f7fbfa", bg=cor, justify="center", cursor="hand2")
		detalhe.pack(pady=(0, 5))
		seta = tk.Label(conteudo, text="→", font=("Segoe UI", 18, "bold"),
						 fg="white", bg=cor, cursor="hand2")
		seta.pack(pady=(0, 12))
		widgets = (sombra, cartao, faixa, conteudo, icone, rotulo, detalhe, seta)
		estado_animacao = {"subindo": True, "ativa": True, "pulso": True}
		direcoes = {"estoque": (0, 1), "vendas": (1, 0), "pedidos": (1, 1)}
		intervalos = {"estoque": 720, "vendas": 540, "pedidos": 420}

		def animar_icone():
			if not icone.winfo_exists():
				return
			dx, dy = direcoes[tipo_icone]
			direcao = 1 if estado_animacao["subindo"] else -1
			icone.move("animado", dx * direcao, dy * direcao)
			estado_animacao["subindo"] = not estado_animacao["subindo"]
			icone.after(intervalos[tipo_icone], animar_icone)

		def pulsar_faixa():
			if not faixa.winfo_exists():
				return
			altura = 7 if estado_animacao["pulso"] else 4
			faixa.configure(height=altura)
			estado_animacao["pulso"] = not estado_animacao["pulso"]
			faixa.after(360, pulsar_faixa)

		def animar(entrando):
			cartao.configure(highlightbackground="white" if entrando else "#CBD5E1")
			sombra.configure(bg="#94A3B8" if entrando else "#CBD5E1")
			seta.configure(text="→" if entrando else "›")
			if entrando:
				conteudo.configure(bg="#" + ("34717a" if tipo_icone == "estoque" else "25845f" if tipo_icone == "vendas" else "b57d2d"))
			else:
				conteudo.configure(bg=cor)

		for widget in widgets:
			widget.bind("<Enter>", lambda _: animar(True), add="+")
			widget.bind("<Leave>", lambda _: animar(False), add="+")
			widget.bind("<Button-1>", lambda _: comando(), add="+")
		animar_icone()
		pulsar_faixa()

	@staticmethod
	def formatar_numero(valor):
		return f"{valor:g}"

	@staticmethod
	def formatar_moeda(valor):
		return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

	def atualizar_tela(self):
		if hasattr(self, "tabela"):
			self.atualizar_tabela()

	def atualizar_tabela(self):
		if not hasattr(self, "tabela"):
			return
		termo = self.pesquisa.get().strip()
		categoria = self.filtro_categoria.get()
		filtro_categoria = "" if categoria == "Todas as categorias" else categoria
		with self.conectar() as banco:
			registros = banco.execute("""SELECT * FROM insumos
				WHERE estabelecimento = ? AND origem = 'estoque'
				AND (nome LIKE ? OR categoria LIKE ? OR fornecedor LIKE ?)
				AND (? = '' OR categoria = ?)
				AND (? = 0 OR quantidade <= estoque_minimo)
				ORDER BY nome""", (self.estabelecimento.get(), f"%{termo}%", f"%{termo}%", f"%{termo}%",
									 filtro_categoria, filtro_categoria, int(self.mostrar_apenas_baixo))).fetchall()
			categorias = [linha[0] for linha in banco.execute("SELECT DISTINCT categoria FROM insumos WHERE estabelecimento = ? AND origem = 'estoque' ORDER BY categoria", (self.estabelecimento.get(),)).fetchall()]
		self.combo_categoria["values"] = ("Todas as categorias", *categorias)
		if self.filtro_categoria.get() not in self.combo_categoria["values"]:
			self.filtro_categoria.set("Todas as categorias")
		for item in self.tabela.get_children():
			self.tabela.delete(item)
		for insumo in registros:
			baixo = insumo["quantidade"] <= insumo["estoque_minimo"]
			self.tabela.insert("", "end", values=(insumo["id"], insumo["nome"], insumo["categoria"],
							  insumo["unidade"], self.formatar_numero(insumo["quantidade"]),
							  self.formatar_numero(insumo["estoque_minimo"]), self.formatar_moeda(insumo["custo"]),
							  insumo["fornecedor"], "ESTOQUE BAIXO" if baixo else "Normal"),
							   tags=("baixo" if baixo else "",))

	def trocar_estabelecimento(self):
		self.titulo_insumos.config(text="Insumos da " + self.estabelecimento.get())
		self.filtro_categoria.set("Todas as categorias")
		self.pesquisa.set("")
		self.atualizar_tela()

	def alternar_filtro_baixo(self):
		self.mostrar_apenas_baixo = not self.mostrar_apenas_baixo
		self.atualizar_tabela()

	def duplicar_insumo(self):
		registro = self.registro_selecionado()
		if registro:
			self.abrir_cadastro(("", registro[1] + " - copia", registro[2], registro[3], "0", "1", registro[6], registro[7]))

	def exportar_csv(self):
		caminho = filedialog.asksaveasfilename(title="Exportar estoque", defaultextension=".csv",
			filetypes=(("Arquivo CSV", "*.csv"), ("Todos os arquivos", "*.*")))
		if not caminho:
			return
		with self.conectar() as banco:
			registros = banco.execute("SELECT nome, categoria, unidade, quantidade, estoque_minimo, custo, fornecedor FROM insumos ORDER BY nome").fetchall()
		with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
			writer = csv.writer(arquivo, delimiter=";")
			writer.writerow(("Insumo", "Categoria", "Unidade", "Quantidade", "Estoque minimo", "Custo", "Fornecedor"))
			for registro in registros:
				writer.writerow(tuple(registro))
		messagebox.showinfo("Exportação concluída", "O estoque foi exportado para um arquivo CSV.")

	def exportar_excel(self):
		momento = datetime.now()
		caminho = filedialog.asksaveasfilename(
			title="Exportar estoque para Excel",
			defaultextension=".xlsx",
			initialfile="estoque_" + self.estabelecimento.get().lower() + "_" + momento.strftime("%Y%m%d_%H%M%S") + ".xlsx",
			filetypes=(("Planilha Excel", "*.xlsx"), ("Todos os arquivos", "*.*")))
		if not caminho:
			return
		with self.conectar() as banco:
			registros = banco.execute("""SELECT nome, categoria, unidade, quantidade, estoque_minimo,
				custo, fornecedor FROM insumos WHERE estabelecimento = ? ORDER BY nome""",
				(self.estabelecimento.get(),)).fetchall()
		cabecalho = ("Insumo", "Categoria", "Unidade", "Quantidade", "Estoque mínimo", "Custo unitário", "Fornecedor", "Situação")
		linhas = [
			(NOME_SISTEMA + " - Estoque", "", "", "", "", "", "", ""),
			("Estabelecimento", self.estabelecimento.get(), "Gerado em", momento.strftime("%d/%m/%Y %H:%M"), "", "", "", ""),
			cabecalho,
		]
		for registro in registros:
			situacao = "ESTOQUE BAIXO" if registro["quantidade"] <= registro["estoque_minimo"] else "Normal"
			linhas.append((registro["nome"], registro["categoria"], registro["unidade"],
				self.formatar_numero(registro["quantidade"]), self.formatar_numero(registro["estoque_minimo"]),
				self.formatar_moeda(registro["custo"]), registro["fornecedor"], situacao))

		def linha_planilha(numero, valores):
			celulas = []
			for indice, valor in enumerate(valores, start=1):
				coluna = ""
				valor_coluna = indice
				while valor_coluna:
					valor_coluna, resto = divmod(valor_coluna - 1, 26)
					coluna = chr(65 + resto) + coluna
				texto = escape(str(valor if valor is not None else ""))
				celulas.append(f'<c r="{coluna}{numero}" t="inlineStr"><is><t>{texto}</t></is></c>')
			return f'<row r="{numero}">' + "".join(celulas) + "</row>"

		linhas_xml = "".join(linha_planilha(numero, valores) for numero, valores in enumerate(linhas, start=1))
		planilha = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
			'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
			'<cols><col min="1" max="1" width="28" customWidth="1"/><col min="2" max="2" width="18" customWidth="1"/>'
			'<col min="7" max="7" width="24" customWidth="1"/></cols><sheetData>' + linhas_xml + '</sheetData></worksheet>')
		workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
			'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
			'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
			'<sheet name="Estoque" sheetId="1" r:id="rId1"/></sheets></workbook>')
		content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
			'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
			'<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
			'<Default Extension="xml" ContentType="application/xml"/>'
			'<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
			'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
		rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
			'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
			'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
		workbook_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
			'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
			'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
		with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as arquivo:
			arquivo.writestr("[Content_Types].xml", content_types)
			arquivo.writestr("_rels/.rels", rels)
			arquivo.writestr("xl/workbook.xml", workbook)
			arquivo.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
			arquivo.writestr("xl/worksheets/sheet1.xml", planilha)
		messagebox.showinfo("Exportação concluída", "Planilha Excel salva em:\n" + caminho)

	def fazer_backup(self):
		if self.nivel_acesso != "administrador":
			return self.executar_com_permissao("administrador", self.fazer_backup)
		momento = datetime.now().strftime("%Y%m%d_%H%M%S")
		caminho = filedialog.asksaveasfilename(
			title="Salvar backup do banco de dados",
			defaultextension=".db",
			initialfile="backup_flexstock_" + momento + ".db",
			filetypes=(("Banco SQLite", "*.db"), ("Todos os arquivos", "*.*")))
		if not caminho:
			return
		try:
			with self.conectar() as origem:
				with sqlite3.connect(caminho) as destino:
					origem.backup(destino)
		except sqlite3.Error as erro:
			messagebox.showerror("Backup não realizado", "Não foi possível criar o backup:\n" + str(erro))
			return
		messagebox.showinfo("Backup concluído", "Backup salvo com sucesso em:\n" + caminho)

	def restaurar_backup(self):
		if self.nivel_acesso != "administrador":
			return self.executar_com_permissao("administrador", self.restaurar_backup)
		caminho = filedialog.askopenfilename(
			title="Selecionar backup do " + NOME_SISTEMA,
			filetypes=(("Banco SQLite", "*.db"), ("Todos os arquivos", "*.*")))
		if not caminho:
			return
		try:
			with sqlite3.connect(caminho) as backup:
				integridade = backup.execute("PRAGMA integrity_check").fetchone()[0]
			if integridade != "ok":
				raise sqlite3.DatabaseError("O arquivo selecionado está corrompido.")
		except (sqlite3.Error, OSError) as erro:
			messagebox.showerror("Backup inválido", "Não foi possível validar o backup:\n" + str(erro))
			return
		confirmado = messagebox.askyesno(
			"Confirmar restauração",
			"A restauração substituirá os dados atuais do estoque. Deseja continuar?")
		if not confirmado:
			return
		try:
			with sqlite3.connect(caminho) as origem:
				with self.conectar() as destino:
					origem.backup(destino)
		except sqlite3.Error as erro:
			messagebox.showerror("Restauração não realizada", "Não foi possível restaurar o backup:\n" + str(erro))
			return
		self.atualizar_tela()
		messagebox.showinfo("Restauração concluída", "Os dados do backup foram restaurados.")

	def exportar_pdf(self):
		momento = datetime.now()
		nome_arquivo = "relatorio_estoque_" + momento.strftime("%Y%m%d_%H%M%S") + ".pdf"
		caminho = os.path.join(os.path.dirname(ARQUIVO_BANCO), nome_arquivo)
		with self.conectar() as banco:
			registros = banco.execute("SELECT nome, categoria, unidade, quantidade, estoque_minimo, custo, fornecedor FROM insumos ORDER BY nome").fetchall()
			resumo = banco.execute("""SELECT COUNT(*) total, COALESCE(SUM(quantidade * custo), 0) valor,
				COALESCE(SUM(CASE WHEN quantidade <= estoque_minimo THEN 1 ELSE 0 END), 0) baixo
				FROM insumos""").fetchone()

		linhas = [
			NOME_SISTEMA + " - RELATORIO DE ESTOQUE",
			"Gerado em: " + momento.strftime("%d/%m/%Y %H:%M"),
			"",
			"Insumos cadastrados: " + str(resumo["total"]) + "    Valor em estoque: " + self.formatar_moeda(resumo["valor"]),
			"Itens com estoque baixo: " + str(resumo["baixo"]),
			"",
			"INSUMO                         CATEGORIA       QTD.   MIN.   CUSTO       SITUACAO",
			"-" * 92,
		]
		for registro in registros:
			situacao = "BAIXO" if registro["quantidade"] <= registro["estoque_minimo"] else "Normal"
			linhas.append("{:<30} {:<16} {:>6} {:>6} {:>10}   {}".format(
				registro["nome"][:30], registro["categoria"][:16], self.formatar_numero(registro["quantidade"]),
				self.formatar_numero(registro["estoque_minimo"]), self.formatar_moeda(registro["custo"]), situacao))

		paginas = [linhas[indice:indice + 42] for indice in range(0, len(linhas), 42)] or [[]]
		objetos = {}
		objetos[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
		objetos[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>"
		paginas_refs = []
		proximo = 4
		for linhas_pagina in paginas:
			pagina_ref, conteudo_ref = proximo, proximo + 1
			proximo += 2
			paginas_refs.append(pagina_ref)
			comandos = ["BT", "/F1 9 Tf", "40 800 Td", "12 TL"]
			for linha in linhas_pagina:
				texto = linha.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
				comandos.append("({}) Tj T*".format(texto))
			comandos.append("ET")
			conteudo = "\n".join(comandos).encode("latin-1", "replace")
			objetos[pagina_ref] = ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
				"/Resources << /Font << /F1 3 0 R >> >> /Contents {} 0 R >>").format(conteudo_ref).encode()
			objetos[conteudo_ref] = b"<< /Length " + str(len(conteudo)).encode() + b" >>\nstream\n" + conteudo + b"\nendstream"
		objetos[2] = ("<< /Type /Pages /Kids [{}] /Count {} >>".format(
			" ".join(str(ref) + " 0 R" for ref in paginas_refs), len(paginas_refs))).encode()

		pdf = bytearray(b"%PDF-1.4\n")
		offsets = [0] * (max(objetos) + 1)
		for numero in range(1, max(objetos) + 1):
			offsets[numero] = len(pdf)
			pdf.extend(str(numero).encode() + b" 0 obj\n" + objetos[numero] + b"\nendobj\n")
		xref = len(pdf)
		pdf.extend(("xref\n0 {}\n0000000000 65535 f \n".format(max(objetos) + 1)).encode())
		for numero in range(1, max(objetos) + 1):
			pdf.extend(("{:010d} 00000 n \n".format(offsets[numero])).encode())
		pdf.extend(("trailer\n<< /Size {} /Root 1 0 R >>\nstartxref\n{}\n%%EOF".format(max(objetos) + 1, xref)).encode())
		with open(caminho, "wb") as arquivo:
			arquivo.write(pdf)
		messagebox.showinfo("PDF gerado", "O relatório do estoque atual foi salvo em:\n" + caminho)
		return caminho

	def baixar_pdf(self):
		arquivo_gerado = self.exportar_pdf()
		if not arquivo_gerado:
			return
		destino = filedialog.asksaveasfilename(title="Baixar relatório PDF", defaultextension=".pdf",
			initialfile=os.path.basename(arquivo_gerado),
			filetypes=(("Arquivo PDF", "*.pdf"), ("Todos os arquivos", "*.*")))
		if not destino:
			return
		shutil.copyfile(arquivo_gerado, destino)
		messagebox.showinfo("Download concluído", "O PDF foi salvo em:\n" + destino)

	def mostrar_historico(self):
		janela = tk.Toplevel(self.janela)
		janela.title("Histórico de movimentações")
		janela.geometry("760x430")
		janela.configure(bg="white")
		tk.Label(janela, text="Últimas movimentações", font=("Georgia", 18, "bold"),
				 foreground="#1f2d35", background="white").pack(anchor="w", padx=22, pady=18)
		area = tk.Frame(janela, bg="white")
		area.pack(fill="both", expand=True, padx=22, pady=(0, 22))
		tabela = ttk.Treeview(area, columns=("data", "insumo", "tipo", "quantidade"), show="headings")
		for coluna, titulo, largura in (("data", "DATA", 160), ("insumo", "INSUMO", 260), ("tipo", "TIPO", 130), ("quantidade", "QUANTIDADE", 120)):
			tabela.heading(coluna, text=titulo)
			tabela.column(coluna, width=largura, anchor="w")
		with self.conectar() as banco:
			registros = banco.execute("""SELECT m.data, i.nome, m.tipo, m.quantidade
				FROM movimentacoes m JOIN insumos i ON i.id = m.insumo_id
				ORDER BY m.id DESC LIMIT 100""").fetchall()
		for registro in registros:
			tabela.insert("", "end", values=(registro["data"], registro["nome"], registro["tipo"], self.formatar_numero(registro["quantidade"])))
		tabela.pack(side="left", fill="both", expand=True)
		rolagem = ttk.Scrollbar(area, orient="vertical", command=tabela.yview)
		rolagem.pack(side="right", fill="y")
		tabela.configure(yscrollcommand=rolagem.set)

	def registro_selecionado(self):
		selecao = self.tabela.selection()
		if not selecao:
			messagebox.showwarning("Nenhum insumo selecionado", "Selecione um insumo na tabela.")
			return None
		return self.tabela.item(selecao[0], "values")

	def mostrar_menu_insumo(self, evento):
		item = self.tabela.identify_row(evento.y)
		if not item:
			return
		self.tabela.selection_set(item)
		self.tabela.focus(item)
		self.menu_insumo.tk_popup(evento.x_root, evento.y_root)

	def abrir_cadastro(self, registro=None, modo_produto=False, ao_salvar=None, modulo="estoque"):
		if self.nivel_acesso not in ("gerente", "administrador"):
			return self.executar_com_permissao("gerente", lambda: self.abrir_cadastro(registro, modo_produto, ao_salvar, modulo))
		janela = tk.Toplevel(self.janela)
		janela.title("Editar insumo" if registro else ("Cadastrar produto" if modo_produto else "Cadastrar insumo"))
		janela.geometry("420x650")
		janela.minsize(420, 650)
		janela.resizable(False, True)
		janela.configure(bg="white")
		campos = {}
		codigo_atual = ""
		if registro:
			with self.conectar() as banco:
				codigo = banco.execute("SELECT codigo_barras FROM insumos WHERE id = ?", (registro[0],)).fetchone()
				codigo_atual = codigo[0] if codigo else ""
		tk.Label(janela, text="Estabelecimento: " + self.estabelecimento.get(), bg="white", fg="#a34f32",
				 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=30, pady=(18, 0))
		rotulo_codigo = "Código do produto" if modo_produto else "Código de barras"
		rotulo_salvar = "Salvar produto" if modo_produto else "Salvar insumo"
		valores = [("Nome do insumo", "nome", registro[1] if registro else ""),
				   ("Categoria", "categoria", registro[2] if registro else "Carnes"),
				   ("Unidade de medida", "unidade", registro[3] if registro else "kg"),
				   ("Quantidade atual", "quantidade", registro[4] if registro else "0"),
				   ("Estoque minimo", "minimo", registro[5] if registro else "1"),
				   ("Custo unitario", "custo", registro[6].replace("R$ ", "").replace(".", "").replace(",", ".") if registro else "0"),
				   ("Fornecedor", "fornecedor", registro[7] if registro else ""),
				   (rotulo_codigo, "codigo_barras", codigo_atual)]
		for rotulo, chave, valor in valores:
			tk.Label(janela, text=rotulo, bg="white", fg="#455a60", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=30, pady=(10, 2))
			entrada = tk.Entry(janela, font=("Segoe UI", 10), relief="solid", bd=1)
			entrada.insert(0, valor)
			entrada.pack(fill="x", padx=30, ipady=5)
			campos[chave] = entrada

		def salvar():
			try:
				nome = campos["nome"].get().strip()
				categoria = campos["categoria"].get().strip()
				unidade = campos["unidade"].get().strip()
				quantidade = float(campos["quantidade"].get().replace(",", "."))
				minimo = float(campos["minimo"].get().replace(",", "."))
				custo = float(campos["custo"].get().replace(",", "."))
				fornecedor = campos["fornecedor"].get().strip()
				codigo_barras = campos["codigo_barras"].get().strip()
				if not nome or not categoria or not unidade or quantidade < 0 or minimo < 0 or custo < 0:
					raise ValueError
			except ValueError:
				messagebox.showerror("Dados invalidos", "Preencha os campos corretamente.", parent=janela)
				return
			dados = (nome, categoria, unidade, quantidade, minimo, custo, fornecedor, codigo_barras)
			with self.conectar() as banco:
				if registro:
					banco.execute("UPDATE insumos SET nome=?, categoria=?, unidade=?, quantidade=?, estoque_minimo=?, custo=?, fornecedor=?, codigo_barras=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
								  dados + (registro[0],))
				else:
					banco.execute("INSERT INTO insumos (nome, estabelecimento, categoria, unidade, quantidade, estoque_minimo, custo, fornecedor, codigo_barras, origem) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
							  (nome, self.estabelecimento.get(), categoria, unidade, quantidade, minimo, custo, fornecedor, codigo_barras, modulo))
			janela.destroy()
			self.mostrar_feedback("Cadastro salvo com sucesso")
			if ao_salvar:
				ao_salvar()
			self.atualizar_tela()

		tk.Button(janela, text=rotulo_salvar, command=salvar, relief="flat", bg="#1f2d35", fg="white",
				  activebackground="#27545a", font=("Segoe UI", 10, "bold"), padx=20, pady=8).pack(pady=18)

	def editar_insumo(self):
		if self.nivel_acesso not in ("gerente", "administrador"):
			return self.executar_com_permissao("gerente", self.editar_insumo)
		registro = self.registro_selecionado()
		if registro:
			self.abrir_cadastro(registro)

	def excluir_insumo(self):
		if self.nivel_acesso != "administrador":
			return self.executar_com_permissao("administrador", self.excluir_insumo)
		registro = self.registro_selecionado()
		if not registro:
			return
		if not messagebox.askyesno("Excluir insumo", f"Excluir '{registro[1]}' do estoque?"):
			return
		with self.conectar() as banco:
			banco.execute("DELETE FROM movimentacoes WHERE insumo_id = ?", (registro[0],))
			banco.execute("DELETE FROM insumos WHERE id = ?", (registro[0],))
		self.atualizar_tela()

	def abrir_movimentacao(self):
		if self.nivel_acesso not in ("gerente", "administrador"):
			return self.executar_com_permissao("gerente", self.abrir_movimentacao)
		registro = self.registro_selecionado()
		if not registro:
			return
		janela = tk.Toplevel(self.janela)
		janela.title("Movimentar estoque")
		janela.geometry("370x270")
		janela.resizable(False, False)
		janela.configure(bg="white")
		tk.Label(janela, text=registro[1], font=("Georgia", 16, "bold"), fg="#1f2d35", bg="white").pack(pady=(22, 4))
		tk.Label(janela, text="Saldo atual: " + registro[4] + " " + registro[3], font=("Segoe UI", 10), fg="#62757a", bg="white").pack(pady=(0, 12))
		tipo = tk.StringVar(value="Entrada")
		ttk.Combobox(janela, textvariable=tipo, values=("Entrada", "Saida"), state="readonly", width=20).pack(pady=4)
		quantidade = tk.Entry(janela, width=22, font=("Segoe UI", 10), relief="solid", bd=1)
		quantidade.insert(0, "1")
		quantidade.pack(pady=12, ipady=5)

		def confirmar():
			try:
				valor = float(quantidade.get().replace(",", "."))
				saldo = float(registro[4].replace(",", "."))
				if valor <= 0 or (tipo.get() == "Saida" and valor > saldo):
					raise ValueError
			except ValueError:
				messagebox.showerror("Movimentacao invalida", "Informe uma quantidade valida e disponivel.", parent=janela)
				return
			ajuste = valor if tipo.get() == "Entrada" else -valor
			with self.conectar() as banco:
				banco.execute("UPDATE insumos SET quantidade = quantidade + ?, atualizado_em=CURRENT_TIMESTAMP WHERE id = ?",
							  (ajuste, registro[0]))
				banco.execute("INSERT INTO movimentacoes (insumo_id, tipo, quantidade) VALUES (?, ?, ?)",
							  (registro[0], tipo.get(), valor))
			janela.destroy()
			self.atualizar_tela()

		tk.Button(janela, text="Confirmar movimentacao", command=confirmar, relief="flat", bg="#16827c", fg="white",
				  activebackground="#12645e", font=("Segoe UI", 10, "bold"), padx=15, pady=8).pack()

	def abrir_leitor_codigo(self):
		janela = tk.Toplevel(self.janela)
		janela.title("Leitor de código de barras")
		janela.geometry("560x360")
		janela.resizable(False, False)
		janela.configure(bg="#eef3f2")
		tk.Label(janela, text="Leitor de código de barras", font=("Georgia", 19, "bold"),
				 foreground="#1f2d35", background="#eef3f2").pack(pady=(24, 4))
		tk.Label(janela, text="Conecte o leitor USB e escaneie o código ou digite-o abaixo.",
				 font=("Segoe UI", 10), foreground="#62757a", background="#eef3f2").pack(pady=(0, 18))
		codigo = tk.Entry(janela, font=("Segoe UI", 16), justify="center", relief="solid", bd=1)
		codigo.pack(fill="x", padx=55, ipady=9)
		resultado = tk.Label(janela, text="Aguardando leitura...", font=("Segoe UI", 11),
				 foreground="#62757a", background="#eef3f2", wraplength=450)
		resultado.pack(pady=22)
		botao_imprimir = tk.Button(janela, text="Imprimir etiqueta térmica", state="disabled",
				 relief="flat", bg="#16827c", fg="white", activebackground="#12645e",
				 font=("Segoe UI", 10, "bold"), padx=15, pady=8)
		botao_imprimir.pack()

		def localizar(_=None):
			valor = codigo.get().strip()
			if not valor:
				return
			with self.conectar() as banco:
				item = banco.execute("""SELECT nome, categoria, unidade, quantidade, estoque_minimo,
					custo, fornecedor, codigo_barras FROM insumos
					WHERE codigo_barras = ? AND estabelecimento = ?""", (valor, self.estabelecimento.get())).fetchone()
			if not item:
				resultado.config(text="Código não encontrado neste estabelecimento.", foreground="#c94b43")
				botao_imprimir.config(state="disabled")
				return
			situacao = "ESTOQUE BAIXO" if item["quantidade"] <= item["estoque_minimo"] else "Normal"
			resultado.config(text=f"{item['nome']}\nQuantidade: {self.formatar_numero(item['quantidade'])} {item['unidade']} | Situação: {situacao}", foreground="#2e6657")
			botao_imprimir.config(state="normal", command=lambda: self.imprimir_etiqueta(item))

		codigo.bind("<Return>", localizar)
		codigo.focus_set()

	def imprimir_etiqueta(self, item):
		texto = (NOME_SISTEMA + "\n" + item["nome"] + "\n" + item["categoria"] +
			"\nCodigo: " + item["codigo_barras"] + "\nEstoque: " +
			self.formatar_numero(item["quantidade"]) + " " + item["unidade"] + "\n")
		comando = b"\x1b@" + texto.encode("cp850", errors="replace") + b"\n\n\x1dV\x00"
		try:
			import win32print # type: ignore
			impressora_padrao = win32print.GetDefaultPrinter()
			nome_impressora = simpledialog.askstring("Impressora térmica", "Nome da impressora:",
				initialvalue=impressora_padrao)
			if not nome_impressora:
				return
			handle = win32print.OpenPrinter(nome_impressora)
			try:
				win32print.StartDocPrinter(handle, 1, ("Etiqueta " + NOME_SISTEMA, None, "RAW"))
				win32print.StartPagePrinter(handle)
				win32print.WritePrinter(handle, comando)
				win32print.EndPagePrinter(handle)
				win32print.EndDocPrinter(handle)
			finally:
				win32print.ClosePrinter(handle)
			messagebox.showinfo("Impressão enviada", "A etiqueta foi enviada para a impressora térmica.")
		except ImportError:
			caminho = filedialog.asksaveasfilename(title="Salvar comando da impressora térmica",
				defaultextension=".prn", filetypes=(("Comando de impressão", "*.prn"),))
			if caminho:
				with open(caminho, "wb") as arquivo:
					arquivo.write(comando)
				messagebox.showinfo("Comando salvo", "Instale o pacote pywin32 para enviar diretamente à impressora.\nArquivo salvo em:\n" + caminho)
		except Exception as erro:
			messagebox.showerror("Falha na impressão", "Não foi possível imprimir a etiqueta:\n" + str(erro))

def abrir_login(janela):
	janela.title("Login - " + NOME_SISTEMA)
	configurar_icone_carrinho(janela)
	janela.geometry("700x480")
	janela.resizable(False, False)
	janela.configure(bg="#f1f5f7")
	with sqlite3.connect(ARQUIVO_BANCO) as banco:
		banco.execute("""CREATE TABLE IF NOT EXISTS usuarios (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			usuario TEXT NOT NULL UNIQUE,
			senha TEXT NOT NULL,
			nivel TEXT NOT NULL DEFAULT 'basico'
		)""")
		colunas = [linha[1] for linha in banco.execute("PRAGMA table_info(usuarios)").fetchall()]
		if "nivel" not in colunas:
			banco.execute("ALTER TABLE usuarios ADD COLUMN nivel TEXT NOT NULL DEFAULT 'basico'")
		for usuario, senha, nivel in (("admin", "1234", "administrador"),
									  ("gerente", "1234", "gerente"), ("operador", "1234", "basico")):
			banco.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, nivel) VALUES (?, ?, ?)",
						  (usuario, hashlib.sha256(senha.encode()).hexdigest(), nivel))
		banco.execute("UPDATE usuarios SET nivel = 'administrador' WHERE usuario = 'admin'")

	frame = tk.Frame(janela, bg="#f1f5f7")
	frame.pack(fill="both", expand=True, padx=18, pady=18)
	painel_marca = tk.Frame(frame, bg="#172a33", width=245)
	painel_marca.pack(side="left", fill="y")
	painel_marca.pack_propagate(False)
	tk.Label(painel_marca, text=NOME_SISTEMA, font=("Georgia", 24, "bold"),
			 foreground="#f0bf62", background="#172a33").pack(anchor="w", padx=28, pady=(48, 6))
	tk.Frame(painel_marca, bg="#d45b45", height=4, width=54).pack(anchor="w", padx=30, pady=(0, 24))
	tk.Label(painel_marca, text=DESCRICAO_SISTEMA.upper(), font=("Segoe UI", 11, "bold"),
			 foreground="#f7fbfa", background="#172a33", justify="left").pack(anchor="w", padx=30)
	tk.Label(painel_marca, text="Uma visão mais clara do\nseu negócio, todos os dias.", font=("Segoe UI", 10),
			 foreground="#9db8ba", background="#172a33", justify="left").pack(anchor="w", padx=30, pady=(14, 0))
	ilustracao_login = tk.Canvas(painel_marca, width=180, height=105, bg="#172a33", highlightthickness=0)
	ilustracao_login.pack(anchor="w", padx=28, pady=(28, 0))
	ilustracao_login.create_line(20, 28, 39, 28, 52, 76, 132, 76, 148, 43, 46, 43, fill="#dce8e5", width=4)
	ilustracao_login.create_line(58, 53, 138, 53, fill="#3f7278", width=3)
	ilustracao_login.create_line(70, 63, 129, 63, fill="#3f7278", width=3)
	ilustracao_login.create_oval(57, 78, 69, 90, fill="#f0bf62", outline="#f0bf62")
	ilustracao_login.create_oval(124, 78, 136, 90, fill="#f0bf62", outline="#f0bf62")
	ilustracao_login.create_rectangle(68, 34, 84, 49, fill="#d45b45", outline="#d45b45")
	ilustracao_login.create_rectangle(90, 27, 108, 49, fill="#16827c", outline="#16827c")
	ilustracao_login.create_rectangle(114, 36, 131, 49, fill="#4c7a99", outline="#4c7a99")
	tk.Label(painel_marca, text="GESTAO OPERACIONAL", font=("Segoe UI", 8, "bold"),
			 foreground="#8eb0ad", background="#172a33").pack(anchor="w", padx=30, pady=(30, 0))

	formulario = tk.Frame(frame, bg="#ffffff", relief="raised", bd=2,
					  highlightbackground="#c2d5d2", highlightthickness=1)
	formulario.pack(side="left", fill="both", expand=True)
	tk.Label(formulario, text="Acesso ao sistema", font=("Segoe UI", 21, "bold"),
			 foreground="#23343b", background="#ffffff").pack(anchor="w", padx=38, pady=(48, 4))
	tk.Label(formulario, text="Entre com suas credenciais para continuar.", font=("Segoe UI", 10),
			 foreground="#71858a", background="#ffffff").pack(anchor="w", padx=40, pady=(0, 30))
	tk.Label(formulario, text="USUARIO", font=("Segoe UI", 8, "bold"),
			 foreground="#62757a", background="#ffffff").pack(anchor="w", padx=40)
	entrada_usuario = tk.Entry(formulario, font=("Segoe UI", 11), relief="solid", bd=1,
						   bg="#f7faf9", fg="#23343b", insertbackground="#d45b45")
	entrada_usuario.pack(fill="x", padx=40, pady=(6, 18), ipady=8)
	tk.Label(formulario, text="SENHA", font=("Segoe UI", 8, "bold"),
			 foreground="#62757a", background="#ffffff").pack(anchor="w", padx=40)
	entrada_senha = tk.Entry(formulario, show="*", font=("Segoe UI", 11), relief="solid", bd=1,
						   bg="#f7faf9", fg="#23343b", insertbackground="#d45b45")
	entrada_senha.pack(fill="x", padx=40, pady=(6, 10), ipady=8)
	status = tk.Label(formulario, text="", font=("Segoe UI", 9), fg="#c94b43", bg="#ffffff")
	status.pack(anchor="w", padx=40, pady=(0, 5))

	def entrar():
		usuario = entrada_usuario.get().strip()
		senha = hashlib.sha256(entrada_senha.get().encode()).hexdigest()
		with sqlite3.connect(ARQUIVO_BANCO) as banco:
			valido = banco.execute("SELECT nivel FROM usuarios WHERE usuario = ? AND senha = ?",
								  (usuario, senha)).fetchone()
		if not valido:
			status.config(text="Usuário ou senha incorretos.")
			entrada_senha.delete(0, tk.END)
			return
		frame.destroy()
		SistemaEstoque(janela, usuario, valido[0])

	botao_entrar = tk.Button(formulario, text="ENTRAR  >", command=entrar, relief="flat", bg="#d45b45", fg="white",
			  activebackground="#b84435", activeforeground="white", font=("Segoe UI", 10, "bold"), padx=20, pady=10)
	botao_entrar.pack(fill="x", padx=40, pady=(4, 0))
	tk.Label(formulario, text="admin: administrador  |  gerente: gerente  |  operador: básico\nSenha inicial: 1234",
			 font=("Segoe UI", 8), foreground="#9a8d82", background="#ffffff").pack(pady=(18, 0))
	aplicar_acabamento_3d(janela)
	entrada_usuario.focus_set()
	entrada_senha.bind("<Return>", lambda _: entrar())


if __name__ == "__main__":
	raiz = tk.Tk()
	abrir_login(raiz)
	raiz.mainloop()

