# Bestiário de D&D 5e

Ferramenta de linha de comando para buscar, registrar e analisar monstros
de D&D 5e usando a API pública Open5e. Os dados são salvos localmente em
SQLite para consulta e análise offline.

## Sobre

Projeto desenvolvido para explorar consumo de APIs externas, persistência
de dados com SQLite e análise de dados com Pandas. O tema é o bestiário
de D&D 5e — criaturas com atributos, ações e níveis de desafio.

## Tecnologias

- Python
- Requests (consumo de API)
- SQLite (persistência local)
- Pandas (análise de dados)
- Tabulate (formatação de tabelas no terminal)

## Funcionalidades

- Buscar monstro por nome via API Open5e
- Filtrar monstros por tipo ou nível de desafio
- Registrar monstros no banco local com todos os atributos e ações
- Sincronizar a base completa de monstros da API para o SQLite
- Gerar relatório com os monstros mais resistentes, ataques mais
  precisos e letalidade média por categoria

## Como rodar

```bash
git clone https://github.com/ArthurFigg/Bestiario_dEd_python.git
cd Bestiario_dEd_python

python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

pip install requests pandas tabulate
python bestiario.py
```

Para gerar o relatório de análise:
```bash
python analise_bestiario.py
```

## Aprendizados

- Consumo de API REST paginada com requests
- Modelagem de banco relacional com SQLite (tabelas com chave estrangeira)
- Extração de dados de texto com regex para normalizar informações da API
- Análise e cruzamento de dados com Pandas e SQL
