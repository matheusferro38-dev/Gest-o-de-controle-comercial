import json
import os
import secrets
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlparse


class NexaStockApi:
	def __init__(self, pasta_sistema, arquivo_estoque, arquivo_vendas, arquivo_pedidos, host="0.0.0.0", porta=8765):
		self.pasta_sistema = pasta_sistema
		self.arquivo_estoque = arquivo_estoque
		self.arquivo_vendas = arquivo_vendas
		self.arquivo_pedidos = arquivo_pedidos
		self.host = host
		self.porta = porta
		self.token = os.environ.get("NEXASTOCK_API_TOKEN") or self._carregar_token()
		self.servidor = None
		self.thread = None

	def _carregar_token(self):
		caminho = os.path.join(self.pasta_sistema, "api_token.txt")
		if os.path.exists(caminho):
			with open(caminho, "r", encoding="utf-8") as arquivo:
				return arquivo.read().strip()
		token = secrets.token_urlsafe(32)
		with open(caminho, "w", encoding="utf-8") as arquivo:
			arquivo.write(token)
		return token

	def conectar(self):
		banco = sqlite3.connect(self.arquivo_estoque)
		banco.row_factory = sqlite3.Row
		banco.execute("ATTACH DATABASE ? AS vendas_db", (self.arquivo_vendas,))
		banco.execute("ATTACH DATABASE ? AS pedidos_db", (self.arquivo_pedidos,))
		return banco

	def iniciar(self):
		api = self

		class Manipulador(BaseHTTPRequestHandler):
			def log_message(self, formato, *argumentos):
				return

			def enviar(self, status, dados):
				corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
				self.send_response(status)
				self.send_header("Content-Type", "application/json; charset=utf-8")
				self.send_header("Content-Length", str(len(corpo)))
				self.send_header("Access-Control-Allow-Origin", "*")
				self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
				self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
				self.end_headers()
				self.wfile.write(corpo)

			def autenticar(self):
				autorizacao = self.headers.get("Authorization", "")
				return autorizacao == "Bearer " + api.token

			def do_OPTIONS(self):
				self.enviar(204, {})

			def do_GET(self):
				if self.path == "/api/health":
					self.enviar(200, {"sistema": "NexaStock", "status": "online", "data": datetime.now().isoformat()})
					return
				if not self.autenticar():
					self.enviar(401, {"erro": "Token inválido ou ausente."})
					return
				url = urlparse(self.path)
				parametros = parse_qs(url.query)
				estabelecimento = parametros.get("estabelecimento", ["Churrascaria"])[0]
				try:
					with api.conectar() as banco:
						if url.path == "/api/estoque":
							registros = banco.execute("""SELECT id, nome, categoria, unidade, quantidade,
								estoque_minimo, custo, fornecedor, atualizado_em FROM main.insumos
								WHERE estabelecimento = ? AND origem = 'estoque' ORDER BY nome""", (estabelecimento,)).fetchall()
							self.enviar(200, {"estabelecimento": estabelecimento, "itens": [dict(registro) for registro in registros]})
						elif url.path == "/api/vendas":
							registros = banco.execute("""SELECT id, usuario, total, forma_pagamento, data
								FROM vendas_db.vendas WHERE estabelecimento = ? ORDER BY id DESC LIMIT 100""", (estabelecimento,)).fetchall()
							self.enviar(200, {"vendas": [dict(registro) for registro in registros]})
						elif url.path == "/api/pedidos":
							registros = banco.execute("""SELECT id, mesa, usuario, total, status, aberto_em, fechado_em
								FROM pedidos_db.pedidos_mesa WHERE estabelecimento = ? ORDER BY id DESC LIMIT 100""", (estabelecimento,)).fetchall()
							self.enviar(200, {"pedidos": [dict(registro) for registro in registros]})
						else:
							self.enviar(404, {"erro": "Endpoint não encontrado."})
				except sqlite3.Error as erro:
					self.enviar(500, {"erro": str(erro)})

			def do_POST(self):
				if not self.autenticar():
					self.enviar(401, {"erro": "Token inválido ou ausente."})
					return
				try:
					quantidade = int(self.headers.get("Content-Length", "0"))
					dados = json.loads(self.rfile.read(quantidade) or b"{}")
				except (ValueError, json.JSONDecodeError):
					self.enviar(400, {"erro": "JSON inválido."})
					return
				try:
					with api.conectar() as banco:
						if self.path == "/api/estoque":
							campos = (dados.get("nome"), dados.get("estabelecimento", "Churrascaria"),
								dados.get("categoria"), dados.get("unidade"), float(dados.get("quantidade", 0)),
								float(dados.get("estoque_minimo", 1)), float(dados.get("custo", 0)),
								dados.get("fornecedor", ""), dados.get("codigo_barras", ""), "estoque")
							if not campos[0] or not campos[2] or not campos[3]:
								raise ValueError("nome, categoria e unidade são obrigatórios")
							cursor = banco.execute("""INSERT INTO main.insumos
								(nome, estabelecimento, categoria, unidade, quantidade, estoque_minimo, custo, fornecedor, codigo_barras, origem)
								VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", campos)
							self.enviar(201, {"id": cursor.lastrowid, "mensagem": "Item cadastrado."})
						else:
							self.enviar(404, {"erro": "Endpoint não encontrado."})
				except (sqlite3.Error, ValueError, TypeError) as erro:
					self.enviar(400, {"erro": str(erro)})

		try:
			api.servidor = ThreadingHTTPServer((api.host, api.porta), Manipulador)
		except OSError:
			return False
		api.thread = Thread(target=api.servidor.serve_forever, daemon=True)
		api.thread.start()
		return True

	def parar(self):
		if self.servidor:
			self.servidor.shutdown()
			self.servidor.server_close()
			self.servidor = None
