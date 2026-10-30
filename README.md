# Sistema de vendas e estoque

Aplicação desenvolvida para o trabalho individual de **Projeto de Banco de Dados**. O objetivo é demonstrar modelagem de dados, operações CRUD e integração com View, Function e Procedure reais do PostgreSQL, usando vendas e estoque como exemplo prático.

No **Trabalho Prático — Integração com Supabase e Redis**, o mesmo sistema evoluiu: os dados passaram a ficar no **Supabase** (PostgreSQL na nuvem) e o **Redis** foi adicionado como cache das leituras mais repetidas. Veja [Integração com Supabase e Redis](#integração-com-supabase-e-redis).

![Visão geral da aplicação](docs/images/visao-geral.jpg)

## Identificação

- **Autor:** Emanuel Cândido da Silva Lima
- **Disciplina:** Projeto de Banco de Dados
- **Professor:** Anderson
- **Entrega prevista no enunciado:** 07/10/2026
- **Repositório:** [EmanuelCandido/Estoque-de-vendas](https://github.com/EmanuelCandido/Estoque-de-vendas).
- **Vídeo explicativo:** [assistir à apresentação no YouTube](https://youtu.be/KqyOtL93yEo).

## Vídeo de apresentação

https://github.com/user-attachments/assets/1415d223-fee3-49f3-ab49-a0857222f1cf

Duração: **4 minutos e 1 segundo**. O vídeo também está no [YouTube](https://youtu.be/KqyOtL93yEo) e, em resolução original e com legendas, em [`docs/videos/apresentacao.mp4`](docs/videos/apresentacao.mp4).

O enunciado pede a apresentação do objetivo, do problema e das funcionalidades; a demonstração das telas; a explicação dos códigos da View, Function e Procedure, com seus parâmetros, resultados e usos; e a demonstração do fluxo da tela até o banco e de volta à aplicação.

## Problema e funcionalidades

Uma pequena loja precisa manter clientes, produtos e estoque organizados, calcular descontos corretamente e registrar uma venda sem deixar os dados inconsistentes.

Funcionalidades disponíveis:

- Visão geral com faturamento, vendas, clientes e alertas de estoque baixo.
- CRUD de produtos: cadastro, consulta, edição e exclusão, com preço e estoque mínimo.
- CRUD de clientes: cadastro, consulta, edição e exclusão.
- Inativação de clientes e produtos sem apagar o histórico de vendas.
- Orçamento com cálculo do total e desconto entre 0% e 100%, com até duas casas decimais.
- Registro de venda com vários itens e baixa automática no estoque.
- Relatório de vendas com filtros de data e detalhamento dos itens.
- Tela **Banco de dados**, com o código SQL e registros das chamadas reais à View, Function e Procedure, útil para a apresentação.
- Tela **Supabase e Redis**, com o servidor e a latência do Supabase, as chaves guardadas no Redis com o tempo de expiração, acertos e faltas do cache, os comandos executados e um botão **Testar cache** que mede a mesma consulta vinda do Supabase e do Redis.

## Tecnologias

- Python 3.10 ou superior; projeto validado com Python 3.12.
- Flask para a API e a página web.
- Psycopg 3 para conexão e consultas parametrizadas.
- PostgreSQL 17, com SQL e PL/pgSQL, hospedado no **Supabase**.
- **Redis** 7, acessado com a biblioteca `redis-py`, como cache.
- Waitress para servir a aplicação local.
- HTML, CSS e JavaScript sem dependências de interface externas.
- unittest para testes de integração em PostgreSQL real.

## Banco de dados

| Tabela | Finalidade |
| --- | --- |
| `clientes` | Dados de contato e situação dos clientes. |
| `produtos` | Catálogo, preços, estoque atual e estoque mínimo. |
| `vendas` | Cliente, data, percentual de desconto e total confirmado. |
| `itens_venda` | Produtos, quantidades e preços praticados em cada venda. |

Uma venda pertence a um cliente e possui vários itens. Cada item se relaciona com um produto. Os nomes e preços utilizados na venda são preservados para que alterações posteriores nos cadastros não reescrevam o histórico.

| Recurso obrigatório | Nome | Finalidade | Integração real |
| --- | --- | --- | --- |
| View | `vw_relatorio_vendas` | Consolidar dados de vendas, clientes e itens. | Relatório: `GET /api/relatorio` executa `SELECT ... FROM vw_relatorio_vendas`. |
| Function | `fn_calcular_total_venda(p_subtotal NUMERIC, p_desconto NUMERIC)` | Aplicar o desconto ao subtotal e retornar o valor final. | Orçamento: `POST /api/orcamento` executa `SELECT fn_calcular_total_venda(...)`. |
| Procedure | `sp_baixar_estoque(p_produto_id INTEGER, p_quantidade INTEGER)` | Reduzir o estoque de um produto vendido. | Nova venda: `POST /api/vendas` executa `CALL sp_baixar_estoque(...)` para cada produto. |

No orçamento, o Python consulta os preços cadastrados, soma preço vezes quantidade e envia o subtotal e o desconto para a Function. Ao confirmar a venda, o Python registra a venda e seus itens, chama a Procedure para baixar o estoque de cada produto e usa a Function para calcular o total. Tudo ocorre na mesma transação: se qualquer etapa falhar, a conexão desfaz as operações.

A Procedure usa apenas um `UPDATE` e um `IF`: reduz o estoque quando o produto está ativo, a quantidade é válida e há unidades suficientes; caso contrário, gera um erro. Por exemplo, `CALL sp_baixar_estoque(1, 2)` dá baixa em duas unidades do produto 1. A condição no próprio `UPDATE` também impede vender a mesma última unidade duas vezes. O Python processa os produtos em ordem de código.

Com 100% de desconto, o total é R$ 0,00. A venda e seus itens são registrados, o estoque é atualizado e o relatório mostra o valor integral como desconto concedido. Valores negativos ou acima de 100% são rejeitados.

![Orçamento com desconto de 100% e total de R$ 0,00](docs/images/orcamento-100.jpg)

## Integração com Supabase e Redis

**Vídeo demonstrativo:** [assistir no GitHub](https://github.com/EmanuelCandido/Estoque-de-vendas/blob/main/docs/videos/supabase-redis.mp4) · [baixar em MP4](https://github.com/EmanuelCandido/Estoque-de-vendas/raw/refs/heads/main/docs/videos/supabase-redis.mp4). Em 2 minutos e 41 segundos, mostra a proposta, as telas, a gravação e a leitura no Supabase, o teste do cache no Redis (MISS e HIT), a invalidação após uma venda e os benefícios. O arquivo também está em `docs/videos/supabase-redis.mp4`.

### Supabase: onde os dados ficam

O Supabase oferece um PostgreSQL gerenciado na nuvem. Como o projeto já era em PostgreSQL, a integração aproveita tudo o que existia: as tabelas, a View `vw_relatorio_vendas`, a Function `fn_calcular_total_venda` e a Procedure `sp_baixar_estoque` são criadas no banco do Supabase pelo próprio iniciador (`scripts/setup_db.py`).

- **Comunicação:** o Flask conecta ao Supabase pela *connection string* do *Session pooler*, lida da variável `DATABASE_URL` no `.env` (`src/config.py` e `src/db.py`). Todas as consultas são parametrizadas.
- **Funcionalidades que usam os dados:** CRUD de produtos e clientes, orçamento (Function), venda com baixa de estoque (Procedure, em uma única transação) e relatório (View). Os dados ficam disponíveis de qualquer computador e podem ser conferidos no **Table Editor** do painel do Supabase.
- **Segurança:** o script `database/supabase/01_seguranca.sql` liga o Row Level Security nas tabelas e retira o acesso das roles `anon` e `authenticated`, fechando a API REST pública do Supabase, já que a aplicação acessa o banco pelo servidor. A senha fica apenas no `.env`, que não vai para o GitHub.
- **Na interface:** a tela **Supabase e Redis** mostra o servidor (`*.pooler.supabase.com`), o banco, a versão, a latência e a quantidade de registros, e o topo da página indica *Supabase conectado*.

### Redis: onde, como e por quê

**Problema:** com o banco na nuvem, cada consulta atravessa a internet. As telas pedem as mesmas leituras o tempo todo: toda abertura do sistema e toda gravação recarregam produtos, clientes e o relatório de vendas, que agrega três tabelas pela View. Os dados mudam bem menos do que são lidos.

**Onde foi usado:** em `src/cache.py`, aplicado às rotas `GET /api/produtos`, `GET /api/clientes` e `GET /api/relatorio` (cada filtro de data tem sua própria chave) em `src/app.py`.

**Como funciona (cache-aside):**

1. A rota procura a chave no Redis, por exemplo `estoque:cache:relatorio:-:-`.
2. Se existe (**HIT**), devolve o JSON guardado, sem acessar o Supabase.
3. Se não existe (**MISS**), consulta o Supabase e grava o resultado no Redis com expiração (`CACHE_TTL`, 60 segundos por padrão).
4. Quando há uma escrita, a aplicação apaga as chaves afetadas (invalidação): uma venda apaga `produtos` e `relatorio`; um cadastro apaga a chave da sua lista. A próxima leitura já vem atualizada do banco.

Acertos, faltas e invalidações ficam contados no próprio Redis (`estoque:stats`). Cada resposta informa a origem no cabeçalho `X-Cache` (`HIT` ou `MISS`) e o tempo no `X-Tempo-Ms`.

**Benefícios:** respostas muito mais rápidas nas leituras repetidas (memória em vez de uma consulta pela internet), menos consultas e conexões no plano gratuito do Supabase e nenhum dado desatualizado após vendas, graças à invalidação. O TTL garante que até uma alteração feita fora do sistema, direto no painel do Supabase, apareça em no máximo 60 segundos.

**Por que o Redis:** guarda tudo em memória, é muito rápido, oferece expiração automática por chave (`SET ... EX`) e é compartilhado entre processos e servidores, ao contrário de um dicionário na memória do Python. Se o Redis estiver fora do ar, a aplicação continua funcionando direto no Supabase.

**Como demonstrar:** abra **Supabase e Redis** e clique em **Testar cache**. A aplicação limpa o cache e faz a mesma consulta duas vezes: a 1ª vem do Supabase (MISS) e a 2ª do Redis (HIT), com os tempos lado a lado. Depois, registre uma venda e volte à tela para ver o comando `DEL` e a nova consulta (MISS) trazendo o estoque atualizado.

### Configurar Supabase e Redis

1. Crie uma conta e um projeto gratuito em [supabase.com](https://supabase.com), de preferência na região São Paulo (`sa-east-1`), e anote a senha do banco.
2. No projeto, clique em **Connect** e copie a URI do **Session pooler**.
3. Para o Redis, use uma das opções:
   - **Nuvem, sem instalar nada:** crie um banco gratuito no [Upstash](https://upstash.com) ou no Redis Cloud e copie a URL que começa com `rediss://`.
   - **Docker:** `docker compose up -d redis` e use `redis://127.0.0.1:6379/0`.
4. Copie `.env.example` para `.env` e preencha `DATABASE_URL` (com a senha no lugar de `[YOUR-PASSWORD]`) e `REDIS_URL`.
5. Execute `iniciar.bat`. Com `DATABASE_URL` preenchida, o iniciador não usa o PostgreSQL portátil: cria as tabelas e os recursos no Supabase, insere os exemplos se o banco estiver vazio e abre a aplicação em `http://127.0.0.1:5000`.

Sem `REDIS_URL`, o sistema funciona sem cache; sem `DATABASE_URL`, usa o PostgreSQL portátil local descrito abaixo.

## Execução rápida no Windows

**Vídeo passo a passo:** [assistir no GitHub](https://github.com/EmanuelCandido/Estoque-de-vendas/blob/main/docs/videos/como-executar.mp4) · [baixar em MP4](https://github.com/EmanuelCandido/Estoque-de-vendas/raw/refs/heads/main/docs/videos/como-executar.mp4). Em 3 minutos e 49 segundos, mostra os pré-requisitos, o download do projeto, a execução do `iniciar.bat`, um teste rápido no navegador, os testes automatizados, como encerrar e o que fazer se algo der errado. O arquivo também está em `docs/videos/como-executar.mp4`.

1. Instale Python 3.10 ou superior, com o comando `python` ou o iniciador `py` disponível no terminal.
2. Dê dois cliques em **`iniciar.bat`** na pasta do projeto.
3. Na primeira execução, aguarde a instalação das dependências e o download do PostgreSQL portátil oficial, de aproximadamente 325 MB. É necessária internet nessa primeira preparação.
4. Abra **[http://127.0.0.1:5000](http://127.0.0.1:5000)**.

O iniciador cria o ambiente virtual, inicia um PostgreSQL real em `127.0.0.1:55432`, cria o banco `estoque_facil`, aplica os scripts e insere exemplos apenas se o banco estiver vazio. Reiniciar preserva os dados já cadastrados.

Para obter o projeto pelo terminal:

```powershell
git clone https://github.com/EmanuelCandido/Estoque-de-vendas.git
cd Estoque-de-vendas
.\iniciar.bat
```

O script `tables/02_limite_desconto.sql` atualiza as restrições dos bancos que ainda usam o limite anterior. A atualização acontece ao iniciar pelo PostgreSQL portátil ou ao executar `scripts/setup_db.py` no banco configurado.

O script `migrations/01_simplificar_rotinas.sql` remove as assinaturas anteriores da Function e da Procedure antes de criar as versões simplificadas. As tabelas e seus registros são preservados.

Alternativa pelo PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\iniciar.ps1
```

Para encerrar a aplicação, pressione `Ctrl+C` no terminal. Para encerrar também o PostgreSQL portátil:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\parar-banco.ps1
```

Os arquivos `.venv/`, `.runtime/` e `.local/` são locais e ignorados pelo Git. A senha do banco portátil é gerada automaticamente e permanece em `.local/`; ela não pertence ao repositório. O iniciador portátil exige Windows de 64 bits.

## PostgreSQL instalado ou Docker

Crie um banco vazio chamado `estoque_facil` no PostgreSQL instalado, ou execute:

```bash
docker compose up -d --wait db
```

Prepare o Python e configure a conexão:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edite DATABASE_URL no arquivo .env, se necessário.
.\.venv\Scripts\python.exe scripts\setup_db.py
.\.venv\Scripts\python.exe -m src.app
```

No Linux/macOS, use `python3 -m venv .venv`, `.venv/bin/python` nos comandos e `cp .env.example .env`. A configuração do exemplo atende ao PostgreSQL do Docker, na porta 5432. O iniciador portátil usa sua própria conexão na porta 55432.

Para instalar diretamente com o cliente `psql` em um banco novo:

```bash
psql -h 127.0.0.1 -U postgres -d estoque_facil -f database/install.sql
```

`install.sql` aplica tabelas, Function, Procedure, View e exemplos dentro de uma transação. Para reaplicar os objetos sem duplicar dados de exemplo, use `scripts/setup_db.py`.

## Exemplo para testar e gravar

1. Em **Orçamento**, adicione 2 unidades de **Mouse sem fio**, a R$ 80 cada.
2. Adicione 1 unidade de **Teclado mecânico**, a R$ 180.
3. Informe **10%** de desconto e clique em **Gerar orçamento**.
4. O subtotal será **R$ 340,00** e o total retornado pela Function será **R$ 306,00**.
5. Clique em **Continuar para venda**, escolha **Ana Oliveira** e confirme.
6. Confira a nova venda no **Relatório de vendas** e a redução de 2 mouses e 1 teclado em **Produtos**.
7. Abra **Banco de dados** para mostrar os scripts e os parâmetros/resultados das chamadas reais.

Os dados iniciais incluem 3 clientes, 6 produtos e 3 vendas, totalizando R$ 1.346,00. A imagem mostra o banco após uma venda adicional realizada na validação. Os valores e estoques aumentam ou diminuem conforme as ações realizadas. A tela de orçamento não altera estoque.

## Testes

Com o banco iniciado:

```powershell
.\.venv\Scripts\python.exe -m pip install fakeredis
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes usam `TEST_DATABASE_URL`, `DATABASE_URL` ou a conexão do banco portátil, nessa ordem. Criam um schema temporário próprio e o removem ao terminar, preservando as tabelas da aplicação. O usuário de teste precisa ter permissão para criar schemas.

São verificados o cache no Redis (MISS, HIT, invalidação após venda, TTL e limpeza, com `fakeredis`), cálculo da Function, descontos de 0% a 100%, venda com total zero, agregação da View, baixa de estoque pela Procedure, gravação da venda, rollback por falta de estoque, CRUD, validações diretamente no banco, atualização das restrições sem perda de dados, preservação de histórico, filtros e duas vendas concorrentes da última unidade. O workflow em `.github/workflows/testes.yml` executa os mesmos testes com PostgreSQL 17 no GitHub Actions após a publicação.

## Organização

```text
src/
  app.py                   API e chamadas SQL reais
  cache.py                 cache das leituras no Redis
  db.py                    conexão e transações
  config.py                variáveis de ambiente
  templates/index.html     estrutura das telas
  static/                  estilos e comportamento da interface
database/
  tables/                  criação das tabelas
  migrations/              atualização das assinaturas antigas
  views/                   vw_relatorio_vendas
  functions/               fn_calcular_total_venda
  procedures/              sp_baixar_estoque
  inserts/                 dados de exemplo
  supabase/                RLS e bloqueio da API pública do Supabase
  install.sql              instalação via psql
  demonstracao.sql          consultas para apresentação
scripts/                   inicialização do banco e PostgreSQL portátil
tests/                     testes de integração
docs/                      modelo, requisitos, execução e vídeos
```

## Documentação e entrega

- [Modelo e fluxo de integração](docs/modelo-banco.md).
- [Referências de interface, técnicas aplicadas e ferramentas úteis](docs/referencias-interface.md).
- [Mapa de atendimento aos requisitos e checklist de entrega](docs/requisitos.md).
- [Atualização do repositório e entrega](docs/publicar-github.md).

O projeto foi preparado para demonstração acadêmica local. Os registros da tela Banco de dados ficam na memória da aplicação e são reiniciados quando o servidor é encerrado.

## Referências técnicas

- [PostgreSQL — CREATE VIEW](https://www.postgresql.org/docs/17/sql-createview.html)
- [PostgreSQL — CREATE FUNCTION](https://www.postgresql.org/docs/17/sql-createfunction.html)
- [PostgreSQL — CREATE PROCEDURE](https://www.postgresql.org/docs/17/sql-createprocedure.html)
- [PostgreSQL — CALL](https://www.postgresql.org/docs/17/sql-call.html)
- [PostgreSQL — binários oficiais para Windows](https://www.postgresql.org/download/windows/)
- [Flask — instalação](https://flask.palletsprojects.com/en/stable/installation/)
- [Psycopg — utilização básica](https://www.psycopg.org/psycopg3/docs/basic/usage.html)
