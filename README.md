# Sprint4-IOT-IOB

Invest Mind – Reconhecimento Facial Integrado
Descrição do Projeto

O sistema desenvolvido tem como objetivo demonstrar a integração prática entre um módulo de reconhecimento facial e uma aplicação web de investimentos.
O reconhecimento facial é responsável pela autenticação do usuário, e o painel web exibe as informações personalizadas após a validação.

O projeto é dividido em dois módulos principais:

Reconhecimento facial (Python + Dlib + SQLite) – faz a detecção, cadastro e validação de rostos.

Aplicação web (Flask + HTML + Tailwind) – exibe o painel do usuário autenticado.

Estrutura do Projeto
invest-mind/
│
├── script.py                         # Código principal de reconhecimento facial
├── dlib_face_recognition_resnet_model_v1.dat
├── shape_predictor_5_face_landmarks.dat
├── faces.db                          # Banco de dados SQLite compartilhado
│
└── webapp/
    ├── app.py                        # Aplicação Flask (painel web)
    └── templates/
        ├── index.html                # Tela inicial (aguarda validação facial)
        └── dashboard.html            # Painel de investimentos após login

Instruções de Execução
1. Instalação dos requisitos

Certifique-se de ter o Python 3.10 ou superior instalado.
Em seguida, instale as dependências:

pip install opencv-python dlib numpy flask


É necessário também ter o CMake instalado no sistema.
Para verificar, execute:

cmake --version

2. Iniciar o servidor web

Dentro da pasta webapp, execute o Flask:

python app.py


O sistema abrirá no endereço:

http://127.0.0.1:5000


Essa página ficará aguardando o reconhecimento facial.

3. Executar o reconhecimento facial

Em outro terminal (fora da pasta webapp), execute:

python script.py


O script abrirá a câmera e iniciará a detecção.

Se o rosto não for encontrado no banco, pressione C para cadastrar.

Se o rosto for reconhecido, ele registra automaticamente a sessão no banco faces.db.

4. Acesso ao painel

Após o reconhecimento facial bem-sucedido, a aplicação Flask detecta automaticamente a sessão ativa no banco de dados e libera o acesso ao painel de investimentos (/dashboard).

O painel exibe:

Nome do usuário autenticado.

Informações simuladas de carteira e desempenho.

Gráfico de alocação e watchlist.

Funcionamento da Integração

A integração entre o reconhecimento facial e o painel web ocorre via banco de dados SQLite compartilhado (faces.db).

O script script.py executa o reconhecimento facial e atualiza a tabela app_session:

user_id → ID do usuário reconhecido

user_name → nome do usuário

started_at → data/hora da autenticação

O aplicativo Flask (app.py) faz requisições constantes ao banco para verificar se há um usuário ativo.

Quando detecta que app_session.user_id está preenchido e recente, considera o usuário autenticado e libera o acesso ao dashboard.

O dashboard carrega os dados simulados de portfólio e mostra a mensagem de boas-vindas com o nome do usuário.

O sistema também conta com tempo de expiração de sessão (10 segundos).
Caso o tempo expire, o acesso é bloqueado e o usuário deve se autenticar novamente via reconhecimento facial.

Estrutura do Banco de Dados

Tabela users
Armazena os usuários cadastrados com seus vetores faciais.

Campo	Tipo	Descrição
id	INTEGER	Identificador único
name	TEXT	Nome do usuário
profile	TEXT	Perfil de investidor
descriptor	TEXT	Vetor facial (128 floats) em JSON
created_at	DATETIME	Data de cadastro

Tabela app_session
Controla a autenticação ativa.

Campo	Tipo	Descrição
id	INTEGER	Sempre igual a 1
user_id	INTEGER	ID do usuário autenticado
user_name	TEXT	Nome do usuário
started_at	DATETIME	Data/hora da autenticação
Conclusão

O sistema cumpre os requisitos de integração entre um módulo de reconhecimento facial e uma aplicação web funcional.
O fluxo é simples, eficiente e demonstra a comunicação prática entre visão computacional e aplicação web, utilizando um banco de dados único para manter a coerência da autenticação.
























🧑‍💻 Autores

Invest Mind – Projeto acadêmico integrador de IoT & IOB

Desenvolvido por: 
Bruno Venturi Lopes Vieira - 99431
Guilherme Alves de Lima - 550433
Pedro Guerra - 99526
Leonardo de Oliveira Ruiz - 98901

Data: Outubro de 2025
