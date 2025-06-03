# app_analise.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re # Para expressões regulares na extração de times

# --- Configurações Iniciais ---
initial_bankroll = 0.00 # BANCA INICIAL AGORA É ZERO

# --- Funções Auxiliares de Limpeza e Processamento ---

@st.cache_data # Cache para não reprocessar dados se o arquivo não mudar
def process_uploaded_file(uploaded_file_content):
    """Lê e processa o arquivo CSV, retornando o DataFrame limpo."""
    df = pd.read_csv(uploaded_file_content)

    # Renomear colunas para padrão interno
    df.rename(columns={
        'Mercado': 'Market/Event Description',
        'Hora de inicio': 'Start Time',
        'Data da última resolução': 'Settled Date',
        'Lucro/Perda (R$)': 'Profit/Loss'
    }, inplace=True)

    # Processamento de datas
    # Funções para substituir abreviações de meses em português por inglês
    month_mapping = {
        'jan': 'Jan', 'fev': 'Feb', 'mar': 'Mar', 'abr': 'Apr',
        'mai': 'May', 'jun': 'Jun', 'jul': 'Jul', 'ago': 'Aug',
        'set': 'Sep', 'out': 'Oct', 'nov': 'Nov', 'dez': 'Dec'
    }
    def replace_portuguese_months(date_str):
        date_str = str(date_str).lower()
        for pt_month, en_month in month_mapping.items():
            date_str = date_str.replace(pt_month, en_month)
        return date_str

    df['Settled Date'] = df['Settled Date'].apply(replace_portuguese_months)
    df['Start Time'] = df['Start Time'].apply(replace_portuguese_months)
    date_format_with_time = '%d-%b-%y %H:%M'
    df['Settled Date'] = pd.to_datetime(df['Settled Date'], format=date_format_with_time, errors='coerce')
    df['Start Time'] = pd.to_datetime(df['Start Time'], format=date_format_with_time, errors='coerce')

    # Processamento de lucro/perda
    def clean_numeric_column(series):
        return series.astype(str).str.strip().astype(float)
    df['Profit/Loss'] = clean_numeric_column(df['Profit/Loss'])

    # Remover linhas com datas não válidas
    df.dropna(subset=['Settled Date'], inplace=True)

    # Ordenar por data para cálculos cumulativos e gráficos
    df = df.sort_values(by='Settled Date').reset_index(drop=True)
    
    return df

def categorize_market_method(description):
    """Categoriza o tipo de mercado com base na descrição."""
    desc_lower = str(description).lower()
    if 'mais/menos' in desc_lower or 'total de gols' in desc_lower or 'gols' in desc_lower:
        return 'Over/Under Gols'
    elif 'placar correto' in desc_lower or 'correct score' in desc_lower:
        return 'Placar Correto'
    elif 'resultado da partida' in desc_lower or 'match odds' in desc_lower or 'resultado final' in desc_lower:
        return 'Resultado Final'
    else:
        return 'Outros'

def extract_individual_teams(description):
    """Extrai nomes de times individuais de uma descrição de mercado."""
    desc_lower = str(description).lower()
    
    # Remove prefixos como "Futebol / " ou "Esporte / "
    desc_lower = re.sub(r'^(futebol|esporte)\s+\/\s*', '', desc_lower).strip()

    # Tenta encontrar o padrão "time1 x time2" ou "time1 vs time2"
    # Adicionado (?:.+?) para capturar o resto da string se houver
    match = re.search(r'(.+?)\s+(x|vs)\s+(.+?)(?:\s*[:(].*|$)', desc_lower) 
    if match:
        team1 = match.group(1).strip()
        team2 = match.group(3).strip()
        
        # Limpezas adicionais nos nomes dos times
        team1 = re.sub(r'\s*\(.+\)\s*', '', team1).strip() # Remove texto entre parênteses
        team2 = re.sub(r'\s*\(.+\)\s*', '', team2).strip()
        
        if team1 and team2: # Certifica-se de que os nomes não estão vazios
            return [team1, team2]
    
    # Fallback: tenta capturar o nome após ' - ' (para Placar Correto - Time) ou similar
    single_team_match = re.search(r'-\s*(.+)', desc_lower)
    if single_team_match:
        team_name = single_team_match.group(1).strip()
        if team_name:
            # Tentar remover o tipo de mercado se estiver no final
            team_name = re.sub(r'\s*(?:resultado da partida|placar correto|mais\/menos de.*gols)\s*$', '', team_name).strip()
            return [re.sub(r'\s*\(.+\)\s*', '', team_name).strip()] # Remove texto entre parênteses

    return ['Time Desconhecido'] # Fallback se nenhum padrão for encontrado

# --- Layout do Aplicativo Streamlit ---
st.set_page_config(
    page_title="Análise de Trading Esportivo - Betfair",
    page_icon="📈",
    layout="wide", # Usa a largura total da tela
    initial_sidebar_state="collapsed"
)

# Título Principal e Introdução
st.title("📈 Análise de Performance de Trading Esportivo")
st.markdown("Bem-vindo à sua ferramenta de análise personalizada para operações na Betfair!")
st.markdown("---")

# Uploader de Arquivo
st.subheader("📤 Faça o Upload do seu Relatório de Lucro/Perda (.csv)")
st.info("Por favor, carregue o arquivo CSV de Lucro/Perda da Betfair. Certifique-se de que ele contém as colunas 'Mercado', 'Hora de inicio', 'Data da última resolução' e 'Lucro/Perda (R$)'.")
uploaded_file = st.file_uploader("Escolha seu arquivo CSV", type="csv")

if uploaded_file is not None:
    # Processa o arquivo usando a função com cache
    df_processed = process_uploaded_file(uploaded_file)

    if df_processed.empty:
        st.warning("⚠️ O arquivo foi lido, mas não há dados válidos após o processamento das datas. Verifique o formato do arquivo e as datas.")
    else:
        st.success("✅ Arquivo carregado e processado com sucesso!")
        st.markdown("---")

        # --- Resumo da Banca ---
        st.header("💰 Resumo da Sua Banca")
        
        # Métricas em colunas
        col1, col2, col3, col4 = st.columns(4) # Divide o espaço em 4 colunas

        total_profit_loss = df_processed['Profit/Loss'].sum()
        current_bankroll = initial_bankroll + total_profit_loss
        
        with col1:
            st.metric(label="Patrimônio Líquido Atual", value=f"R$ {current_bankroll:,.2f}")
        
        with col2:
            max_profit = df_processed[df_processed['Profit/Loss'] > 0]['Profit/Loss'].max()
            st.metric(label="Maior Lucro Individual", value=f"R$ {max_profit:,.2f}" if pd.notna(max_profit) else "N/A")

        with col3:
            max_loss = df_processed[df_processed['Profit/Loss'] < 0]['Profit/Loss'].min()
            st.metric(label="Maior Perda Individual", value=f"R$ {max_loss:,.2f}" if pd.notna(max_loss) else "N/A")
            
        with col4:
            df_processed['Settled Day'] = df_processed['Settled Date'].dt.to_period('D')
            daily_profit_loss_avg = df_processed.groupby('Settled Day')['Profit/Loss'].sum().mean()
            st.metric(label="Lucro/Perda Média por Dia", value=f"R$ {daily_profit_loss_avg:,.2f}" if pd.notna(daily_profit_loss_avg) else "N/A")

        st.markdown("---")

        # --- Crescimento da Banca ao Longo do Tempo ---
        st.header("📈 Crescimento da Banca ao Longo do Tempo")
        df_processed['Cumulative Profit/Loss'] = df_processed['Profit/Loss'].cumsum()
        df_processed['Bankroll History'] = initial_bankroll + df_processed['Cumulative Profit/Loss']

        fig_bankroll, ax_bankroll = plt.subplots(figsize=(10, 5))
        ax_bankroll.plot(df_processed['Settled Date'], df_processed['Bankroll History'], marker='o', linestyle='-', markersize=4, color='#1f77b4') # Azul bonito
        ax_bankroll.set_title('Evolução do Patrimônio da Banca')
        ax_bankroll.set_xlabel('Data de Resolução')
        ax_bankroll.set_ylabel('Patrimônio da Banca (R$)')
        ax_bankroll.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        st.pyplot(fig_bankroll)
        st.markdown("---")

        # --- Análise por Método de Entrada ---
        st.header("📊 Análise por Método de Entrada")
        df_processed['Market Method'] = df_processed['Market/Event Description'].apply(categorize_market_method)

        method_analysis = df_processed.groupby('Market Method').agg(
            Quantidade=('Market Method', 'size'),
            Lucro_Prejuizo_Total=('Profit/Loss', 'sum')
        ).sort_values(by='Lucro_Prejuizo_Total', ascending=False)
        
        st.dataframe(method_analysis.style.format({"Lucro_Prejuizo_Total": "R$ {:,.2f}"}).set_caption("Resumo por Tipo de Método"))

        st.markdown("---")

        # --- Análise por Times Individuais ---
        st.header("⚽ Análise de Lucro/Perda por Times Individuais")
        df_processed['Individual Teams'] = df_processed['Market/Event Description'].apply(extract_individual_teams)
        
        # Explode a lista de times para ter uma linha por time envolvido em cada entrada
        df_teams_exploded = df_processed.explode('Individual Teams')
        
        # Remover 'Time Desconhecido' se não for desejado na análise de times
        team_profit_loss = df_teams_exploded[
            df_teams_exploded['Individual Teams'] != 'time desconhecido'
        ].groupby('Individual Teams')['Profit/Loss'].sum().sort_values(ascending=False)

        col_teams1, col_teams2 = st.columns(2)

        with col_teams1:
            st.subheader("Times Mais Lucrativos (Top 5)")
            st.dataframe(team_profit_loss.head(5).to_frame(name="Lucro/Prejuízo").style.format({"Lucro/Prejuízo": "R$ {:,.2f}"}).set_caption("Times com maior lucro"))

        with col_teams2:
            st.subheader("Times Menos Lucrativos (Top 5)")
            st.dataframe(team_profit_loss.tail(5).to_frame(name="Lucro/Prejuízo").style.format({"Lucro/Prejuízo": "R$ {:,.2f}"}).set_caption("Times com maior prejuízo"))

        st.markdown("---")

        # --- Observações Finais ---
        st.info("⚠️ **Observações Importantes:**")
        st.info("ROI (Return on Investment): Não é possível calcular. A coluna 'Valor Apostado' (Stake) não está presente neste arquivo.")
        st.info("Odd Média das Entradas: Não é possível calcular. A coluna 'Cotações' (Odds) não está presente neste arquivo.")

else:
    st.info("Aguardando o upload do arquivo CSV para iniciar a análise.")

st.markdown("---")
st.markdown("Feito com ❤️ por uma IA para Traders Esportivos.")