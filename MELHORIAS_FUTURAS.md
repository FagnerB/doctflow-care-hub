# Melhorias futuras

Itens feios-mas-funcionais notados durante o trabalho, fora do escopo da tarefa em andamento. Não mexer sem aprovação explícita.

- **`__pycache__`/`*.pyc` do backend estão versionados no git.** `doctflow-care-hub/.gitignore` não tem padrões Python (`__pycache__/`, `*.pyc`), então todo `git status` mostra dezenas de arquivos binários "modificados" que não são código. Não afeta funcionamento, só polui diffs. Corrigir exigiria adicionar ao `.gitignore` e rodar `git rm -r --cached` nos arquivos já rastreados — mudança de repositório, não de código, então fica pra quando for pedida.
