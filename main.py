
"""
Script realizado por fathooo.
linkedin: https://www.linkedin.com/in/fathooo/
web: www.fathooo.com/

Este script nace a raíz de la necesidad de conocer el contenido que compone
el diario, en este caso, un diario local de la ciudad de Chillán. 
"""



#%%
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import os
import errno


#%%   ----------------inicialización

url = 'http://www.ladiscusion.cl'
link_re = re.compile(r'^https?:\/\/[\w\-]+(\.[\w\-]+)+[/#?]?.*$')
dir_path_data = "./data"
dir_path_content = './data_content'


class Html_extractor:
    def __init__(self, url : str):
        self.url = url
        self.soup = self.get_soup()

    def get_soup(self):
        solicitud = requests.get(self.url, 'html.parser')
        if solicitud.status_code == 200:
            print('Conexión exitosa: {}'.format(self.url))
            soup = BeautifulSoup(solicitud.content, 'html.parser')
            return soup
        else:
            print('Conexión fallida: {}'.format(solicitud.status_code))

class Cleaner_regex:
    def clean_name_links(url):
        limpieza_links = re.compile(r'https:\/\/(www)?\.?(ladiscusion.cl)?\/?(category)?\/?(\w+)\/?(\w+)?\/?()?(.ladiscusion.cl\/)?')
        patron = limpieza_links.search(url)
        if patron.group(4) and patron.group(5):
            name = '{}_{}'.format(patron.group(4), patron.group(5))
            return name
        else:
            name = '{}'.format(patron.group(4))
            return name

    def clean_date_regex(date):
        clean_date_regex = r"(.{1,})T(.{1,})-(.{1,})"
        patron = re.compile(clean_date_regex)
        patron = patron.search(date)
        date = '{} {}'.format(patron.group(1), patron.group(2))
        return date 

    def clean_content_regex(content):
        content_search = re.sub(r'\n', ' ', content)
        content_search = re.sub(r'\s+', ' ', content_search)
        return content_search

class DfCreator:
    def create_df_href(nav_links):
        for link in nav_links:
            index = nav_links.index(link)
            try:
                lista_links = get_links_per_page(link)
                dict_list = {nav_links[index]: lista_links}
                df = pd.DataFrame(dict_list)
                nombre = Cleaner_regex.clean_name_links(link)
                df.to_parquet('{}/{}.parquet'.format(dir_path_data,nombre), index= False)
            except:
                print('No se pudo obtener la lista de links de la página {}'.format(link))
                continue

    def create_df_content_per_page(pages):
        df_content_full = pd.DataFrame()

        for page in pages:
            soup = Html_extractor(page).soup
            try:
                title = soup.find('h1', attrs={'class': 'entry-title'}).text
                date = soup.find('time', attrs={'class': 'entry-date'})['datetime']
                content = soup.find('div', attrs={'class': 'entry-content'})
                if content.button:
                    content.button.decompose()
                content = content.text

                subtitles_text =[]
                subtitles = soup.find_all('h4')
                if subtitles:
                    for i in subtitles:
                        subtitles_text.append(i.span.text)

                df_content = pd.DataFrame()
                df_content['link'] = [page]
                df_content['title'] = [title]
                df_content['date'] = [date]
                df_content['content'] = [content]
                n = 0
                for i in subtitles_text:
                    index = 'subtitle_{}'.format(n)
                    n += 1
                    df_content[index] = [i]
                
                df_content_full = df_content_full.append(df_content)

            except:
                print('No se pudo obtener el contenido de la página {}'.format(page))
                continue
            
            
        
        df_content_full = df_content_full.reset_index(drop=True)
        return df_content_full

class Validator_inSecuence:
    def __init__(self, secuence, rangeofList):
        self.secuence = secuence
        self.is_valid = True
        self.rangeofList = len(rangeofList)
        self.error_message = []
        self.validations = []

    def validate(self):
        secuence = self.secuence
        secuence_split = secuence.split(',')
        validations_len = []
        validations = []

        for i in secuence_split:
            try:
                digits = bool((re.match(r'(\s+)?(\d+)(\s+)?', i)))
                letters = bool((re.match(r'(\s+)?[a-zA-Z](\s+)?', i)))
                space = bool((re.match(r'[\s+]', i)))
                space_with_letters = bool((re.match(r'(\s+)?[a-zA-Z](\s+)?', i)))
                nothing = bool(i == '')

                if digits and bool(int(i) >= self.rangeofList):
                    self.error_message.append('Numero invalido: {}'.format(i))
                    continue
        
                if digits or nothing or space:
                    if space_with_letters:
                        self.error_message.append('Secuencia invalida: {}'.format(i))
                        continue
                    else:
                        validations_len.append(i)
                if digits:
                    validations.append(int(i))
        
            except:
                self.error_message.append('Secuencia invalida: {}'.format(i))
                continue

        if len(secuence_split) == len(validations_len):
            validations = set(validations)
            self.is_valid = True
            self.validations = list(validations)
            return self.is_valid

        else:
            self.is_valid = False
            print('\n\n ')
            for i in self.error_message:
                print(i)
            print('\n\n ')
            return self.is_valid

def get_links_per_page(url):
    link = Html_extractor(url).soup
    links = []
    active = True

    while active:
        try:
            links_notices = link.find('div', attrs={'class': 'qlm-list'}).find_all('h2')
            for i in links_notices:
                links.append(i.a['href'])
                
            try:
                next_button = link.find('div', attrs={'class': 'nav-links'}).find('a', attrs= {'class': 'next'})['href']
                if next_button is not None:
                    link = Html_extractor(next_button).soup  
            except:
                active = False
                return links
        except:
            active = False
            return links

def create_dir(dir):
    try:
        os.mkdir(dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def treatment_df(df, name):
    try:
        df['date'] = df['date'].apply(lambda x: Cleaner_regex.clean_date_regex(x))
        df['date'] = pd.to_datetime(
                df['date'],
                errors = 'coerce',
                format ='%Y/%m/%d %H:%M:%S'
        )   
        df['content'] = df['content'].apply(lambda x: Cleaner_regex.clean_content_regex(x))
        return df 
    except:
        print('No se pudo procesar el DataFrame: {}'.format(name))
        return df

def pages(archive, archives):   
    try: 
        archive.validate()
        pages = []

        if archive.is_valid:
            for i in archive.validations:
                df = pd.read_parquet('{}/{}'.format(dir_path_data, archives[i]))
                pages.append(df[df.columns.values[0]].values.tolist())

        return pages
    except:
        return False

def select_1(on, response):
    on = on
    response = response

    soup = Html_extractor(url).soup
    nav_li_href = soup.nav.ul.find_all('a', attrs={'href': link_re})
    nav_list_links = [link['href'] for link in nav_li_href]

    if int(response):
        while on:
            try: 
                if response == '1':
                    DfCreator.create_df_href(nav_list_links)
                    print('\n\n Archivos creados \n\n')
                    on = False

                if response == '2':
                    print('\n Seleccione el archivo que desea descargar: \n')
                    print('Si quieres más de uno, puedes ingresar los numeros separados por una coma. \n')
                                
                    for i in nav_list_links:
                        print('[{}] - {}'.format(nav_list_links.index(i), i))
                                
                    select_2 = input('\n Respuesta: ')

                    validator = Validator_inSecuence(select_2, nav_list_links)
                    validator.validate()

                    if validator.is_valid:
                        for i in validator.validations:
                                DfCreator.create_df_href([nav_list_links[i]])     
                        on = False
                    else:
                        print('\n\n Te enviaremos al menu principal por tu respuesta erronea, Intenta solo ingresar numeros y comas \n\n')
                        on = False

                if response == '3':
                    print('\n')
                    on = False
            except:
                print('\n\n Te enviaremos al menu principal. \n\n')
                on = False

        return False
    else:
        print('\n\n Opción inválida \n\n')
        return False

def select_2(on, response):
    on = on
    response = response
    archives = os.listdir(dir_path_data)

    if int(response):
        while on:
            try:
                if response == '1':
                    pages_per_parquet = []

                    for i in archives:
                        df = pd.read_parquet('{}/{}'.format(dir_path_data, i))
                        pages_per_parquet.append(df[df.columns.values[0]].values.tolist())

                    for page in pages_per_parquet:
                        name = str(archives[pages_per_parquet.index(page)])
                        df_content = DfCreator.create_df_content_per_page(page)
                        df_content_t = treatment_df(df_content, name)
                        df_content_t.to_parquet('{}/{}'.format(dir_path_content, 'content_{}'.format(name)))
                        print('\n\n Archivos creados \n\n')

                    on = False

                elif response == '2':
                    print('Seleccione el archivo que desea leer: \n')
                    print('Si quieres más de uno, puedes ingresar los numeros separados por una coma.')

                    for i in archives:
                        print('[{}] - {}'.format(archives.index(i), i))

                    response_2 = input('\n Respuesta: ')

                    archive = Validator_inSecuence(response_2, archives)
                    pages_per_parquet = pages(archive, archives)
                    archive.validate()

                    for page in pages_per_parquet:
                        name = str(archives[archive.validations[pages_per_parquet.index(page)]])
                        df_content = DfCreator.create_df_content_per_page(page)
                        df_content_t = treatment_df(df_content, name)
                        df_content_t.to_parquet('{}/{}'.format(dir_path_content, 'content_{}'.format(name)))

                    on = False
                    
                elif response == '3':
                    on = False
                    
            except:
                print('\n\n Ocurrió un error inesperado \n\n')
                on = False
            
        return False

    else:
        print('\n\n Opción inválida \n\n')
        return False

def main():
    active = True
    create_dir(dir_path_data)
    create_dir(dir_path_content)

    while active:
        select = input('Ingrese\n [1] para crear archivos de datos\n [2] Extraer datos de categorías\n [3] para salir:\nRespuesta: ')
        print(select + '\n')
        try: 
            if select == '1':
                on = True
                while on:
                    print('------------------------------------------------------')
                    response = input('Ingrese\n [1] para extraer todos los datos\n [2] para extraer uno en especifico\n [3] Atrás\n Respuesta: ')
                    print('------------------------------------------------------')
                    on = select_1(on, response)
                continue

            elif select == '2':
                on = True
                while on:
                    print('------------------------------------------------------')
                    response = input('Ingrese\n [1] Para escrapear todos los datos de la carpeta data\n [2] Scrapear archivos en especifico\n [3] Atrás\n Respuesta: ')
                    on = select_2(on, response)
                continue

            elif select == '3':
                active = False
        except:
            print('\n\n Opción inválida \n\n') 
            continue
            
#%%
if __name__ == '__main__':
    main()

    