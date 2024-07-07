# Gerenciador de Consultas Médicas

## Descrição
O projeto consiste em um sistema de gerenciamento de consultas médicas. O sistema permite:
- Visualização de médicos cadastrados de uma determinada especialidade
- Visualização de horários disponíveis para um determinado médico
- Visualização de consultas marcadas para um determinado paciente
- Marcação de novas consultas
- Atualização de consultas existentes
- Exclusão de consultas

## Execução com Docker

### Requisitos

1. Ter o [Docker](https://docs.docker.com/engine/install/) instalado

### Execução
1. A partir da pasta raiz em um terminal como administrador, executar o comando abaixo para criar a imagem do Docker:

   `docker build -t gerenciador-consultas .`
2. No mesmo terminal, executar o comando abaixo para executar o container:

   `docker run -p 5000:5000 gerenciador-consultas`

## Execução sem Docker

### Requisitos

1. Ter o Python 3 instalado na máquina
2. Executar o comando abaixo para instalar as dependências:

   `pip install -r requirements.txt`

### Execução

Para executar a API, execute o comando abaixo a partir desta pasta:

`python -m flask run --port 5000`

