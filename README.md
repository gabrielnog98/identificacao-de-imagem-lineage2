# Monitor de Tela com Detecção de Imagem

Este projeto é uma aplicação desenvolvida em Python para monitorar a tela em tempo real e detectar a presença de imagens de referência previamente definidas. A detecção é realizada com OpenCV por meio de correspondência de padrões, permitindo identificar elementos visuais na tela com base em um nível mínimo de confiança configurável.

Quando uma das imagens de referência é encontrada, o sistema emite um alerta sonoro automático, auxiliando o usuário a perceber rapidamente a ocorrência do evento monitorado.

## Tecnologias utilizadas

- Python
- OpenCV
- NumPy
- MSS
- Winsound
- Threading

## Funcionalidades

- Monitoramento da tela em tempo real;
- Detecção de múltiplas imagens de referência;
- Ajuste de nível mínimo de confiança;
- Suporte à detecção em diferentes escalas;
- Alerta sonoro automático;
- Possibilidade de monitorar a tela inteira ou uma região específica.
