import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from fpdf import FPDF
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Validador Fiscal Provincial", page_icon="🏛️", layout="wide")

# Headers para parecer un navegador real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- FUNCIONES DE CONSULTA ---

def consultar_arba(cuit):
    """
    Intenta consultar la deuda pública de ARBA mediante la URL directa.
    """
    url = f"https://consultas.arba.gov.ar/ConsultasGenerales/recuperarEstadoDeuda.do?action=recuperarEstadoDeuda&cuit={cuit}"
    try:
        # ARBA suele responder rápido, usamos verify=False por si acaso
        r = requests.get(url, headers=HEADERS, verify=False, timeout=10)
        
        if r.status_code == 200:
            if "No registra deuda" in r.text or "SIN DEUDA" in r.text.upper():
                return "✅ Sin Deuda Registrada"
            elif "Total de Deuda" in r.text:
                return "⚠️ Registra Deuda / Planes (Verificar en web)"
            else:
                return "ℹ️ Consultar manualmente (Respuesta no estándar)"
        else:
            return f"Error HTTP {r.status_code}"
    except Exception as e:
        return "Error de conexión (Posible bloqueo)"

def consultar_corrientes(cuit):
    """
    Consulta DGR Corrientes por URL directa.
    """
    url = f"https://www.dgrcorrientes.gob.ar/Informacionutil/gestiontransparente/consultacontribuyente/{cuit}"
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=10)
        if r.status_code == 200:
            if "No se registran datos" in r.text or "inexistente" in r.text:
                return "✅ Sin antecedentes registrados"
            else:
                return "⚠️ Contribuyente ACTIVO / Registrado"
        else:
            return f"Error HTTP {r.status_code}"
    except:
        return "Error de conexión"

def consultar_cordoba(cuit):
    """
    Rentas Córdoba es más complejo (requiere interacción JS). 
    Devolvemos el link directo para facilitar la tarea.
    """
    return "🔗 Verificación Manual Requerida"

# --- GENERACIÓN DE PDF ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Informe de Situación Fiscal', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf(datos):
    pdf = PDFReport()
    pdf.add_page()
    
    # Datos Generales
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"CUIT Consultado: {datos['cuit']}", ln=True)
    pdf.cell(0, 10, f"Fecha de Consulta: {time.strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)
    
    # Tabla de Resultados
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "Resultados de Organismos Provinciales", 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    # Configuración de columnas
    pdf.set_font("Arial", "B", 11)
    pdf.cell(60, 10, "Organismo", 1)
    pdf.cell(0, 10, "Resultado / Estado", 1, 1)
    
    pdf.set_font("Arial", "", 11)
    
    # ARBA
    pdf.cell(60, 10, "ARBA (Buenos Aires)", 1)
    pdf.cell(0, 10, datos['arba'], 1, 1)
    
    # Corrientes
    pdf.cell(60, 10, "DGR Corrientes", 1)
    pdf.cell(0, 10, datos['corrientes'], 1, 1)
    
    # Córdoba (Nota especial)
    pdf.cell(60, 10, "Rentas Córdoba", 1)
    pdf.cell(0, 10, "Verificación manual (Sistema interactivo)", 1, 1)
    
    pdf.ln(10)
    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(0, 8, "Nota: Este informe es una consolidación automática de datos públicos. Verifique siempre en la web oficial para fines legales.")
    
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ PRINCIPAL ---

def main():
    st.title("🏛️ Validador Fiscal (Sin BCRA)")
    st.markdown("Consulta rápida de estado en ARBA y DGR Corrientes.")
    
    with st.form("form_consulta"):
        cuit_input = st.text_input("Ingrese CUIT (11 dígitos):", max_chars=11)
        submitted = st.form_submit_button("🔎 Consultar Organismos")
        
        if submitted:
            if len(cuit_input) == 11 and cuit_input.isdigit():
                
                with st.spinner("Conectando con fiscos provinciales..."):
                    # Ejecutamos las consultas reales
                    res_arba = consultar_arba(cuit_input)
                    res_corrientes = consultar_corrientes(cuit_input)
                    res_cordoba = consultar_cordoba(cuit_input)
                    
                    # Guardamos resultados
                    datos = {
                        "cuit": cuit_input,
                        "arba": res_arba,
                        "corrientes": res_corrientes,
                        "cordoba": res_cordoba
                    }
                    
                    st.success("Consulta Finalizada")
                    
                    # Mostrar Tarjetas de Resultado
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.subheader("Prov. Bs. As.")
                        if "Sin Deuda" in res_arba:
                            st.success(res_arba)
                        elif "Error" in res_arba:
                            st.error(res_arba)
                        else:
                            st.warning(res_arba)
                            st.markdown(f"[Ver Web ARBA](https://consultas.arba.gov.ar/ConsultasGenerales/recuperarEstadoDeuda.do?action=recuperarEstadoDeuda&cuit={cuit_input})")
                            
                    with col2:
                        st.subheader("Corrientes")
                        if "Sin antecedentes" in res_corrientes:
                            st.success(res_corrientes)
                        else:
                            st.info(res_corrientes)
                            st.markdown(f"[Ver Web DGR](https://www.dgrcorrientes.gob.ar/Informacionutil/gestiontransparente/consultacontribuyente/{cuit_input})")

                    with col3:
                        st.subheader("Córdoba")
                        st.info("Consulta Web Requerida")
                        st.markdown("[Ir a Rentas Córdoba](https://www.rentascordoba.gob.ar/gestiones/consulta/situacion-fiscal)")

                    st.divider()
                    
                    # Botón PDF
                    pdf_bytes = generar_pdf(datos)
                    st.download_button(
                        label="📄 Descargar Informe PDF",
                        data=pdf_bytes,
                        file_name=f"Fiscal_{cuit_input}.pdf",
                        mime="application/pdf",
                        type="primary"
                    )
            else:
                st.warning("Por favor ingrese un CUIT válido.")

if __name__ == "__main__":
    main()
