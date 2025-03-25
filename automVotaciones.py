import time
import random
import re
import requests
import os
from selenium import webdriver
from selenium.webdriver.support.ui import Select 
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from faker import Faker
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from TempMail import TempMail
from bs4 import BeautifulSoup


# --- Configuración del navegador ---
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# --- URLs ---
url_registro = "https://www.zona-interactiva.canalrcn.com/register"
url_votacion = "https://www.zona-interactiva.canalrcn.com/la-casa-de-los-famosos/votaciones/votaciones-salvacion"

fake = Faker("es_CO")  # Genera nombres en español (Colombia)

# --- Función para generar un correo temporal con TempMail ---
def generar_correo():
    tmp = TempMail()  # Crear objeto TempMail
    inbox = tmp.createInbox()  # Generar un correo aleatorio
    correo = inbox.address  # Obtener la dirección de correo
    token = inbox.token  # Obtener el token único
    print(f"📩 Correo generado: {correo}")
    print(f"🔑 Token de correo: {token}")
    return tmp, inbox

# --- Función para obtener el código de verificación ---
def obtener_codigo_verificacion(tmp, inbox):
    print("⏳ Esperando el código de verificación...")    
    for _ in range(6):  # Intentar durante 1 minuto (6 intentos x 10 segundos)
        try:
            emails1 = tmp.getEmails(inbox)
            
            if not emails1:
                print("📭 No hay correos en la bandeja de entrada aún.")
            else:
                print("\n📨 Correos recibidos:")
                for email in emails1:
                    print(f"✉️ Remitente: {email.sender}")
                    print(f"📩 Destinatario: {email.recipient}")
                    print(f"📜 Asunto: {email.subject}")                    
                    print(f"🕒 Fecha: {email.date}\n")
                
                if "Código de verificación del Canal RCN" in email.subject:
                    soup = BeautifulSoup(email.html, "html.parser")  # Convertir HTML a BeautifulSoup                    
                    verification_code = None
                    h4_tags = soup.find_all("h4", style=True)  # Busca todos los <h4> con un atributo `style`

                    for h4 in h4_tags:
                        if "text-align: center" in h4["style"] and h4.find("span"):
                            verification_code = h4.find("span").text.strip()
                            if verification_code.isdigit():  # Verifica que sea un número
                                break  # Detiene la búsqueda al encontrarlo

                    if verification_code:
                        print(f"✅ Código de verificación: {verification_code}")
                        return verification_code 
                    else:
                        print("❌ No se encontró el código de verificación.")
                        return verification_code                       
        except Exception as e:
            print(f"❌ Error al obtener la bandeja de entrada: {e}")                                   
        time.sleep(12)
    print("❌ No se recibió código a tiempo")
    return None

# --- Función principal para registrar y votar ---
def registrar_y_votar():
    intentos = 0
    while True:  # Bucle infinito hasta que se bloquee
        intentos += 1
        print(f"\n🔄 Intento #{intentos} de votación...")

        tmp, inbox = generar_correo()
        if not inbox:
            continue

        # Datos de registro
        nombre = fake.first_name()
        apellido = fake.last_name()
        telefono = f"3{random.randint(100000000, 999999999)}"
        contraseña = "ClaveSegura123!"

        try:
            # driver.set_window_position(2000,0)
            # driver.maximize_window()        

            # --- Registro ---
            driver.get(url_registro)
            time.sleep(1)
            driver.find_element(By.NAME, "full_name").send_keys(nombre)                        

            driver.find_element(By.NAME, "last_name").send_keys(apellido)

            select_element = driver.find_element(By.NAME, "country_code")
            select = Select(select_element)
            select.select_by_value("34")

            driver.find_element(By.NAME, "phone").send_keys(telefono)
            driver.find_element(By.NAME, "email").send_keys(inbox.address)            

            driver.find_element(By.NAME, "password").send_keys(contraseña)
            driver.find_element(By.NAME, "password_confirmation").send_keys(contraseña)

            try:
                # Intentar encontrar y hacer clic en el botón de aceptar cookies
                cookies_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Entendido')]")
                cookies_button.click()
                print("✅ Aviso de cookies cerrado.")
                time.sleep(1)
            except NoSuchElementException:
                print("⚠️ No se encontró el aviso de cookies, continuando...")

            driver.find_element(By.NAME, "accepted_terms").click()
            driver.find_element(By.NAME, "accepted_data_processing").click()

            try:
                continuar_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//button[@data-testid='submitStep1']"))
                )
                print("✅ Botón encontrado.")
                
                if continuar_button.is_displayed() and continuar_button.is_enabled():                    
                    continuar_button.click()
                    continuar_button.click()
                    print("✅ Cuenta registrada")
                    time.sleep(1)            
                else:
                    print("❌ El botón NO está visible o habilitado.")

                error_texto = "Ups! Parece que ya tienes una cuenta con este correo electrónico"
                if error_texto in driver.page_source:
                    print("⚠️ Error: El correo ya está registrado. Reiniciando...")
                    registrar_y_votar()

            except Exception as e:
                print(f"❌ No se encontró el botón 'Continuar': {e}")
                                    

            # --- Verificación ---
            codigo = obtener_codigo_verificacion(tmp, inbox)
            if not codigo:
                print("❌ No se recibió ningún código de verificación.")
                return
            inputs = driver.find_elements(By.XPATH, "//div[@class='code']/input")
            for i in range(len(inputs)):
                inputs[i].send_keys(codigo[i])
            driver.find_element(By.XPATH, "//button[contains(text(), 'Siguiente')]").click()
            print("✅ Cuenta verificada")
            time.sleep(5)

            # --- Votación ---
            driver.get(url_votacion)
            time.sleep(3)
            # driver.find_element(By.XPATH, "//div[contains(text(), 'Juan Ricardo Lozano 'Alerta'')]").click()
            opcion = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'template_desktop_1_opcion')]//span[contains(text(), 'Melissa Gate')]"))
            )
            opcion.click()
            
            votar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'VOTAR')]"))
            )
            votar.click()
            print("✅ Voto registrado")                      
            time.sleep(5)            

            try:
                # Esperar hasta que el botón esté visible y sea clickeable
                boton_logout = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "logout_header"))
                )

                # # Hacer scroll hasta el botón por si está fuera de la vista
                # ActionChains(driver).move_to_element(boton_logout).perform()

                # Hacer click en el botón
                boton_logout.click()
                print("✅ Se hizo clic en 'Cerrar Sesión'.")
                time.sleep(3)
            
            except Exception as e:
                print(f"❌ Error al intentar cerrar sesión: {e}")

        except Exception as e:
            print(f"❌ Error: {e}")

        finally:
            time.sleep(15)  # Esperar antes de repetir el proceso

# --- Ejecutar el proceso ---
registrar_y_votar()