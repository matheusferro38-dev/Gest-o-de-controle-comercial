# API Wi-Fi do NexaStock

A API inicia automaticamente junto com o sistema na porta `8765` e aceita conexoes na rede local.

## Endereco

Use o IPv4 do computador que executa o NexaStock:

`http://IP_DO_COMPUTADOR:8765`

O token de acesso fica salvo no arquivo `api_token.txt` e deve ser enviado no cabecalho:

`Authorization: Bearer SEU_TOKEN`

## Endpoints

- `GET /api/health` - verifica se o sistema esta online. Nao exige token.
- `GET /api/estoque?estabelecimento=Churrascaria` - lista produtos do estoque.
- `GET /api/vendas?estabelecimento=Churrascaria` - lista as ultimas vendas.
- `GET /api/pedidos?estabelecimento=Churrascaria` - lista pedidos de mesa.
- `POST /api/estoque` - cadastra um produto no estoque.

Exemplo de JSON para cadastro:

```json
{
  "nome": "Refrigerante",
  "estabelecimento": "Churrascaria",
  "categoria": "Bebidas",
  "unidade": "unidade",
  "quantidade": 20,
  "estoque_minimo": 5,
  "custo": 4.5,
  "fornecedor": "Distribuidora Central",
  "codigo_barras": "7890000000000"
}
```

A API usa os bancos separados `estoque.db`, `vendas.db` e `pedidos.db`.
