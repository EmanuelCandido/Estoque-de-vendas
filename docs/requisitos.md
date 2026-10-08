# Requisitos e entrega

| Exigência do enunciado | Implementação / evidência |
| --- | --- |
| Aplicação CRUD | Produtos e clientes com criação, leitura, edição e exclusão. |
| Pelo menos uma View real | `database/views/01_relatorio_vendas.sql`. |
| View utilizada em tela | Relatório de vendas, através de `GET /api/relatorio`. |
| Pelo menos uma Function real | `database/functions/01_calcular_total_venda.sql`. |
| Function utilizada em funcionalidade | Gerar orçamento; cálculo também reutilizado ao confirmar a venda. |
| Pelo menos uma Procedure real | `database/procedures/01_baixar_estoque.sql`. |
| Procedure chamada pela aplicação | Confirmar venda, através de `POST /api/vendas` e `CALL`. |
| Três telas/funcionalidades com os recursos | Orçamento, Nova venda e Relatório de vendas. |
| Finalidades diferentes e justificadas | Cálculo, baixa de estoque e consolidação para consulta. |
| Scripts de tabelas e inserts | `database/tables/` e `database/inserts/`. |
| Possibilidade de recriar o banco | `database/install.sql`, `scripts/setup_db.py` e iniciador portátil. |
| Código organizado | `src/`, `database/`, `docs/`, `scripts/`, `tests/`. |
| README com identificação e execução | `README.md`, disciplina Projeto de Banco de Dados, professor Anderson. |
| Repositório no GitHub | [EmanuelCandido/Estoque-de-vendas](https://github.com/EmanuelCandido/Estoque-de-vendas). |
| Vídeo explicativo | [Vídeo de apresentação no YouTube](https://youtu.be/KqyOtL93yEo), também vinculado no README. |

## Conferência antes de entregar em 07/10/2026

- [x] Conferir o nome do autor no README.
- [x] Confirmar que o repositório está público ou acessível ao professor.
- [x] Verificar que código, scripts e documentação estão no GitHub.
- [x] Abrir a aplicação e conferir os dados de exemplo.
- [ ] Gravar a apresentação do objetivo, problema e funcionalidades.
- [ ] Demonstrar as principais telas.
- [ ] Mostrar código, motivo, tabelas, resultado e tela da View.
- [ ] Mostrar código, operação, parâmetros, retorno e uso da Function.
- [ ] Mostrar código, parâmetros, operações e tela que chama a Procedure.
- [ ] Comprovar o fluxo tela → chamada → recurso do banco → resultado.
- [x] Acrescentar o link do vídeo ao README.
- [ ] Enviar os links do repositório e do vídeo conforme orientação da disciplina.

O vídeo gravado está disponível no [YouTube](https://youtu.be/KqyOtL93yEo), com link no README e cópia em `docs/videos/apresentacao.mp4`. Confira os tópicos acima antes de enviar os links ao professor.
