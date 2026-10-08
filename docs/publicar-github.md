# Repositório e entrega

Repositório do trabalho: [EmanuelCandido/Estoque-de-vendas](https://github.com/EmanuelCandido/Estoque-de-vendas).

## Obter uma cópia

```powershell
git clone https://github.com/EmanuelCandido/Estoque-de-vendas.git
cd Estoque-de-vendas
.\iniciar.bat
```

Os requisitos e as alternativas de instalação estão no [README](../README.md).

## Enviar alterações

Depois de editar e testar o projeto, confira os arquivos antes de enviá-los:

```powershell
git status
git add .
git diff --cached --stat
git commit -m "Atualiza o projeto de banco de dados"
git push origin main
```

O `.gitignore` exclui o ambiente virtual, os dados e as credenciais do banco local, os logs e as configurações do editor. O arquivo `.env.example` contém apenas a configuração de exemplo para o PostgreSQL do Docker.

Na aba **Actions** do GitHub, o workflow **Testes PostgreSQL** verifica a integração com um banco PostgreSQL 17.

## Finalizar a entrega

1. Confirme que o repositório está público ou acessível ao professor.
2. Grave o vídeo mostrando os códigos SQL e seu uso nas telas.
3. Substitua o campo pendente do vídeo no README pelo link da gravação.
4. Envie os links do repositório e do vídeo conforme a orientação da disciplina.

O prazo informado no enunciado é **07/10/2026**.
