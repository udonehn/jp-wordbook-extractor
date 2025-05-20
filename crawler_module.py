from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager # ChromeDriver 자동 관리
from bs4 import BeautifulSoup
import time
import os
import csv

class NaverWordbookCrawler:
    def __init__(self, status_callback=None):
        self.driver = None
        self.status_callback = status_callback # GUI 업데이트를 위한 콜백 함수
        self.current_selenium_page = 1 # 단어 카드 목록 페이지 내에서의 현재 페이지 번호

    def _log_status(self, message):
        """GUI 또는 콘솔에 진행 상황 메시지를 로깅합니다."""
        if self.status_callback:
            self.status_callback(message)
        else:
            print(message)

    def setup_driver_and_navigate(self, url):
        """WebDriver를 설정하고 주어진 URL로 이동합니다."""
        if self.driver: # 이미 드라이버가 실행 중인 경우
            try:
                self._log_status(f"이미 실행 중인 브라우저로 {url} 페이지로 이동합니다...")
                self.driver.get(url)
                # 페이지 로드 완료 확인 (document.readyState)
                WebDriverWait(self.driver, 15).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                self._log_status("페이지 이동 완료.")
                # 단어장 목록 페이지로 이동한 것이므로, 페이지 번호는 여기서 초기화하지 않음
                return
            except Exception as e:
                self._log_status(f"기존 브라우저로 페이지 이동 중 오류: {e}. 새 브라우저를 시도합니다.")
                self.quit_driver() # 기존 드라이버 문제 시 종료 후 새로 시작

        # WebDriver 옵션 설정
        options = webdriver.ChromeOptions()
        options.add_experimental_option('excludeSwitches', ['enable-logging']) # 콘솔 로그 줄이기
        options.add_argument("--disable-gpu") # GUI 없는 환경 또는 일부 시스템에서 필요
        options.add_argument("--log-level=3") # Selenium 로그 레벨 설정

        try:
            self._log_status("ChromeDriver 자동 설정 중...")
            service = ChromeService(ChromeDriverManager().install()) # ChromeDriver 자동 설치 및 경로 설정
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(60) # 페이지 로드 최대 대기 시간 (초)
            self._log_status("WebDriver가 성공적으로 설정되었습니다.")
            
            self._log_status(f"{url} 페이지로 이동합니다...")
            self.driver.get(url)
            # 페이지의 기본 구조(예: <div id="wrap">)가 로드될 때까지 대기
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.ID, 'wrap'))
            )
            self._log_status("페이지 기본 로드 완료. 브라우저에서 직접 로그인을 진행해주세요.")
        except Exception as e:
            self._log_status(f"WebDriver 설정 또는 페이지 이동 중 오류 발생: {e}")
            self.quit_driver() # 실패 시 드라이버 정리
            raise # 오류를 호출한 곳으로 다시 전달하여 GUI에 표시되도록 함

    def select_wordbook(self, wordbook_name_to_find):
        """
        현재 열려있는 단어장 목록 페이지에서 지정된 이름의 단어장을 찾아 클릭합니다.
        성공 시 True, 실패 시 False를 반환합니다.
        """
        self._log_status(f"단어장 목록 페이지에서 '{wordbook_name_to_find}' 단어장을 찾는 중...")
        try:
            # 단어장 목록을 포함하는 컨테이너(#main_folder)가 화면에 보일 때까지 대기
            folder_list_container = WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located((By.ID, 'main_folder'))
            )
            # 실제 단어장 목록(ul.list_folder) 가져오기
            actual_list_ul = folder_list_container.find_element(By.CSS_SELECTOR, 'ul.list_folder')
            
            self._log_status("단어장 목록 로드 확인됨. 단어장 검색 시작...")
            wordbook_items = actual_list_ul.find_elements(By.CSS_SELECTOR, 'li.item_folder._item_folder') # 각 단어장 항목
            
            if not wordbook_items:
                self._log_status("단어장 목록(li.item_folder)이 비어있습니다. 단어장을 추가했는지 확인해주세요.")
                return False

            found_link_element = None
            for item_idx, item_element in enumerate(wordbook_items):
                try:
                    # 각 단어장 항목 내의 링크(a) 태그와 이름(span.name) 태그를 찾음
                    link_tag = item_element.find_element(By.CSS_SELECTOR, 'a.folder_inner._btn_cards_link')
                    name_span = link_tag.find_element(By.CSS_SELECTOR, 'div.folder_tit span.name')
                    current_wordbook_name = name_span.text.strip() # 단어장 이름 텍스트 추출 및 공백 제거
                    
                    self._log_status(f"  {item_idx+1}. 발견된 단어장: '{current_wordbook_name}'") # 찾은 단어장 이름 로깅
                    
                    if current_wordbook_name == wordbook_name_to_find: # 사용자가 입력한 이름과 일치하는지 확인
                        found_link_element = link_tag
                        self._log_status(f"성공: '{wordbook_name_to_find}' 단어장을 찾았습니다.")
                        break # 일치하는 단어장을 찾으면 루프 종료
                except NoSuchElementException:
                    self._log_status(f"  {item_idx+1}. 단어장 항목 내 이름 태그(span.name)를 찾지 못했습니다. 다음 항목으로 넘어갑니다.")
                    continue # 현재 항목에서 구조가 다르거나 이름이 없으면 다음 항목으로
            
            if found_link_element:
                self._log_status(f"'{wordbook_name_to_find}' 단어장으로 이동합니다...")
                # 클릭하기 전에 해당 요소가 화면에 보이도록 스크롤 (필요시)
                self.driver.execute_script("arguments[0].scrollIntoView(true);", found_link_element)
                time.sleep(0.3) # 스크롤 후 안정화 시간
                found_link_element.click() # 단어장 링크 클릭
                
                # 단어 카드 목록 페이지로 성공적으로 이동했는지 확인
                # 1. URL에 '#/my/cards'가 포함될 때까지 대기
                WebDriverWait(self.driver, 15).until(lambda driver: "#/my/cards" in driver.current_url)
                # 2. 단어 카드 섹션(#section_word_card)이 화면에 보일 때까지 대기
                WebDriverWait(self.driver, 20).until(
                    EC.visibility_of_element_located((By.ID, 'section_word_card'))
                )

                self.current_selenium_page = 1 # 단어 카드 목록의 첫 페이지로 진입했으므로 페이지 번호 초기화
                self._log_status("단어 카드 목록 페이지로 성공적으로 이동했습니다.")
                return True
            else:
                self._log_status(f"실패: '{wordbook_name_to_find}' 이름의 단어장을 목록에서 찾을 수 없습니다. 정확한 이름을 입력했는지 확인해주세요.")
                return False

        except TimeoutException:
            self._log_status("단어장 목록 또는 특정 요소를 찾는 중 시간 초과되었습니다. 페이지가 올바르게 로드되었는지, 로그인이 정상적으로 되었는지 확인해주세요.")
            return False
        except Exception as e:
            self._log_status(f"단어장 선택 중 예상치 못한 오류 발생: {e}")
            return False

    def _extract_words_from_current_page(self):
        """현재 페이지에서 단어 정보를 추출하여 CSV 행 데이터 리스트로 반환합니다."""
        if not self.driver:
            self._log_status("오류: WebDriver가 초기화되지 않았습니다.")
            return []
        
        try:
            # 단어 카드 섹션 로드 대기
            self._log_status("단어 카드 섹션(#section_word_card) 로딩 대기 중...")
            main_card_section = WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located((By.ID, 'section_word_card'))
            )
            self._log_status("'section_word_card' 로드 및 확인됨.")

            # 실제 단어 카드(inner_card) 로드 대기
            self._log_status("실제 단어 카드(inner_card) 로딩 대기 중...")
            try:
                WebDriverWait(main_card_section, 10).until( 
                    EC.visibility_of_element_located((By.CLASS_NAME, 'inner_card'))
                )
                self._log_status("최소 하나의 'inner_card' 로드 및 확인됨.")
                time.sleep(0.5) # 모든 카드가 완전히 로드되도록 약간의 추가 시간
            except TimeoutException:
                self._log_status("시간 내에 'inner_card'를 찾지 못했습니다. 이 페이지에 단어가 없거나 로드되지 않았을 수 있습니다.")
                return [] 
        except TimeoutException:
            self._log_status("'section_word_card'를 시간 내에 찾거나 볼 수 없었습니다. 로그인이 올바르게 되었는지, 단어장 페이지가 맞는지 확인해주세요.")
            self._log_status(f"현재 URL: {self.driver.current_url}")
            return []
        except Exception as e:
            self._log_status(f"단어 추출 준비 중 예기치 않은 예외 발생: {e}")
            return []

        html = self.driver.page_source # 현재 페이지의 HTML 소스 가져오기
        soup = BeautifulSoup(html, 'html.parser') # HTML 파싱
        
        # 파싱된 HTML에서 단어 카드 섹션 찾기
        section_for_soup = soup.find('div', id='section_word_card')
        if not section_for_soup:
            self._log_status("'section_word_card'를 파싱된 HTML에서 찾을 수 없습니다.")
            return []
            
        inner_cards = section_for_soup.findAll('div', class_='inner_card') # 모든 단어 카드 추출
        page_data_for_csv = [] # 현재 페이지에서 추출한 단어 데이터를 담을 리스트

        if not inner_cards:
            self._log_status("파싱된 HTML에서 'inner_card' 요소를 찾을 수 없습니다. (단어가 없는 페이지일 수 있습니다)")
            return []

        # 각 단어 카드(inner_card) 순회
        for card_idx, inner_card_div in enumerate(inner_cards):
            hiragana_text = ''
            kanji_text = ''
            parts_of_speech_set = set() # 품사 수집용 (중복 제거)
            meanings_list = []          # 순수 뜻 목록
            examples_list = []          # 예문 목록 (일어-한국어 쌍으로 저장)
            memo_text = ''              # 메모 내용

            # 1. 단어 (히라가나 및 한자) 추출
            word_item_div = inner_card_div.find('div', class_='item_word')
            if word_item_div:
                title_tag = word_item_div.find('a', class_='title')
                if title_tag:
                    raw_word = title_tag.get_text(separator=" ", strip=True).replace('-', '') # 공백 기준으로 텍스트 합치고 하이픈 제거
                    if '[' in raw_word and ']' in raw_word: # 한자 포함 여부 확인
                        parts = raw_word.split('[', 1)
                        hiragana_text = parts[0].strip()
                        kanji_text = parts[1].replace(']', '').strip()
                    else: # 한자 없는 경우
                        hiragana_text = raw_word.strip()
                        kanji_text = hiragana_text # 한자가 없으면 히라가나를 한자 필드에도 동일하게
            
            # 2. 품사, 뜻 및 관련 예문 추출
            wrap_mean_div = inner_card_div.find('div', class_='wrap_mean')
            if wrap_mean_div:
                # 각 뜻 항목(li.item_mean) 순회
                item_mean_tags = wrap_mean_div.select('ul.list_mean > li.item_mean')
                for item_mean_tag in item_mean_tags:
                    mean_desc_div = item_mean_tag.find('div', class_='mean_desc') # 뜻 설명 부분
                    if mean_desc_div:
                        # 품사 추출
                        part_speech_tag = mean_desc_div.find('em', class_='part_speech')
                        if part_speech_tag:
                            pos_text = part_speech_tag.get_text(strip=True)
                            if pos_text: # 실제 품사 텍스트가 있을 경우에만 추가
                                parts_of_speech_set.add(pos_text)
                        
                        # 순수 뜻 내용 추출 (p.cont 내부에서 품사 태그를 제외한 텍스트)
                        p_cont_tag = mean_desc_div.find('p', class_='cont')
                        meaning_text_only = ""
                        if p_cont_tag:
                            # p.cont 태그의 내용을 복사하여 BeautifulSoup으로 다시 파싱 (원본 DOM 변경 방지)
                            temp_p_cont_soup = BeautifulSoup(str(p_cont_tag), 'html.parser')
                            temp_p_tag_inner = temp_p_cont_soup.find('p') # 복사된 p 태그
                            if temp_p_tag_inner:
                                for em_tag in temp_p_tag_inner.find_all('em', class_='part_speech'): # 품사 태그(em) 제거
                                    em_tag.decompose()
                                meaning_text_only = temp_p_tag_inner.get_text(strip=True) # 순수 텍스트만 추출
                        elif mean_desc_div: # p.cont가 없고 mean_desc에 직접 텍스트가 있는 예외적인 경우 대비
                            temp_mean_desc_soup = BeautifulSoup(str(mean_desc_div), 'html.parser')
                            temp_div_inner = temp_mean_desc_soup.find('div')
                            if temp_div_inner:
                                for em_tag in temp_div_inner.find_all('em', class_='part_speech'): em_tag.decompose()
                                for num_tag in temp_div_inner.find_all('span', class_='num'): num_tag.decompose() # 뜻 번호도 제거
                                meaning_text_only = temp_div_inner.get_text(strip=True)
                        
                        if meaning_text_only: # 추출된 순수 뜻이 있을 경우에만 리스트에 추가
                            meanings_list.append(meaning_text_only.strip())

                    # 해당 뜻(li.item_mean)에 대한 예문 추출
                    example_ul_tag = item_mean_tag.find('ul', class_='example') # 예문 목록 (ul)
                    if example_ul_tag:
                        item_example_tags = example_ul_tag.findAll('li', class_='item_example') # 각 예문 항목 (li)
                        for ex_tag in item_example_tags:
                            origin_p = ex_tag.find('p', class_='origin') # 일본어 예문
                            translate_p = ex_tag.find('p', class_='translate') # 한국어 번역
                            if origin_p and translate_p:
                                examples_list.append(origin_p.get_text(strip=True))
                                examples_list.append(translate_p.get_text(strip=True))
            
            # 3. 메모 추출
            wrap_memo_div = inner_card_div.find('div', class_='wrap_memo') # 메모 전체 래퍼
            if wrap_memo_div:
                # 메모가 실제로 화면에 보이는지 (style 또는 class 속성으로 확인)
                style_attr = wrap_memo_div.get('style', '')
                class_attr = wrap_memo_div.get('class', [])
                # 'display: none'이 아니고, 'view' 클래스가 있거나, 'display: block'이거나, style 속성이 아예 없는 경우 (보이는 상태로 간주)
                if 'display: none' not in style_attr and \
                   ('view' in class_attr or 'display: block' in style_attr or style_attr.strip() == ''):
                    # 실제 메모 내용은 div._temp_memo (보통 보이는 텍스트) 또는 textarea._memo_area (편집 시)에 있음
                    temp_memo_div = wrap_memo_div.find('div', class_='_temp_memo')
                    if temp_memo_div and temp_memo_div.get_text(strip=True): # 보이는 div에 내용이 있으면 우선 사용
                        memo_text = temp_memo_div.get_text(strip=True)
                    else: # 아니면 textarea에서 찾기
                        memo_textarea = wrap_memo_div.find('textarea', class_='_memo_area')
                        if memo_textarea:
                             memo_text = memo_textarea.get_text(strip=True) # textarea의 값 가져오기

            # 추출된 데이터를 CSV 한 행으로 정리
            final_pos_str = ", ".join(sorted(list(parts_of_speech_set))) # 수집된 품사들을 정렬하여 문자열로
            final_meaning_str = "\n".join(m for m in meanings_list if m) # 여러 뜻은 줄바꿈으로 구분
            
            # 예문 형식: (일어1)\n(번역1)\n\n(일어2)\n(번역2)...
            formatted_examples = []
            for i in range(0, len(examples_list), 2): # 2개씩 (일어, 번역) 쌍으로 처리
                if i+1 < len(examples_list):
                    formatted_examples.append(f"{examples_list[i]}\n{examples_list[i+1]}")
            final_example_str = "\n\n".join(formatted_examples) # 각 예문 쌍은 두 번의 줄바꿈으로 구분

            page_data_for_csv.append([
                hiragana_text,
                kanji_text,
                final_pos_str,      # 품사
                final_meaning_str,  # 순수 뜻
                final_example_str,  # 예문
                memo_text           # 메모
            ])
        return page_data_for_csv

    def _navigate_to_next_page(self):
        """현재 단어 카드 목록 페이지에서 다음 페이지로 이동합니다."""
        if not self.driver: 
            self._log_status("오류: WebDriver가 초기화되지 않아 페이지 이동 불가.")
            return False
        
        next_page_to_click = self.current_selenium_page + 1 # 이동할 다음 페이지 번호
        self._log_status(f"다음 페이지({next_page_to_click})로 이동 시도...")

        try:
            # 페이지네이션 영역(div#page_area)이 나타날 때까지 대기
            page_area = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'page_area'))
            )
            
            # 다음 페이지 번호에 해당하는 버튼 XPath (텍스트 기반 검색)
            next_page_button_xpath = f".//ul[@id='page_list']//button[contains(@class, 'page_num') and normalize-space(text())='{next_page_to_click}']"
            
            try:
                # 페이지네이션 영역 내에서 다음 페이지 버튼 검색
                next_page_button = page_area.find_element(By.XPATH, next_page_button_xpath)
            except NoSuchElementException:
                self._log_status(f"페이지 {next_page_to_click} 버튼을 찾을 수 없습니다. 마지막 페이지일 가능성이 높습니다.")
                return False # 다음 페이지 버튼 없음

            if next_page_button.is_displayed() and next_page_button.is_enabled(): # 버튼이 보이고 활성화되어 있다면
                # 클릭 전 스크롤하여 버튼이 보이도록 함 (필요시)
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_page_button)
                time.sleep(0.2) # 스크롤 후 잠시 대기
                self.driver.execute_script("arguments[0].click();", next_page_button) # JavaScript로 클릭 (더 안정적일 수 있음)
                
                # 페이지 이동 및 로딩 대기
                # 1. 클릭된 페이지 번호 버튼이 'is-active' 클래스를 가질 때까지 대기
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, f"{next_page_button_xpath}[contains(@class, 'is-active')]"))
                )
                # 2. 새 페이지의 단어 카드 섹션(#section_word_card)이 화면에 보일 때까지 대기
                WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located((By.ID, 'section_word_card'))
                )
                time.sleep(1.0) # DOM 안정화 및 추가 JS 실행 대기

                self.current_selenium_page = next_page_to_click # 현재 페이지 번호 업데이트
                self._log_status(f"성공적으로 {self.current_selenium_page} 페이지로 이동했습니다.")
                return True
            else:
                self._log_status(f"페이지 {next_page_to_click} 버튼이 클릭 가능한 상태가 아닙니다.")
                return False
        except TimeoutException:
            self._log_status(f"페이지 {next_page_to_click}로 이동 또는 로드 확인 중 시간 초과.")
            return False
        except Exception as e:
            self._log_status(f"페이지 이동 중 예기치 않은 오류 발생: {e}")
            return False

    def crawl_wordbook_pages(self, num_pages, output_filepath):
        """지정된 페이지 수만큼 단어장 페이지를 크롤링하여 CSV 파일로 저장합니다."""
        if not self.driver:
            self._log_status("오류: WebDriver가 설정되지 않았습니다. '브라우저 열기'를 먼저 실행해주세요.")
            raise Exception("WebDriver 미설정. 브라우저를 먼저 열어주세요.")

        all_data_for_csv = [] # 모든 페이지에서 추출한 데이터를 모을 리스트
        
        # 사용자가 요청한 페이지 수만큼 반복 (1페이지부터 시작)
        for i in range(1, num_pages + 1):
            self._log_status(f"요청 {i}/{num_pages} 페이지 (실제 브라우저: {self.current_selenium_page} 페이지) 데이터 추출 시도...")
            
            try:
                # 페이지가 완전히 로드될 때까지 (document.readyState) 대기
                WebDriverWait(self.driver, 15).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except TimeoutException:
                self._log_status(f"{self.current_selenium_page} 페이지 로드 상태 확인 시간 초과. 계속 진행 시도.")

            # 현재 보이는 페이지에서 단어 데이터 추출
            page_csv_data = self._extract_words_from_current_page() 
            
            # 첫 페이지만 확인 (이후 페이지는 _navigate_to_next_page에서 존재 여부 판단)
            if not page_csv_data and i == 1 and self.current_selenium_page == 1 :
                self._log_status("첫 페이지에서 단어를 가져오지 못했습니다. 단어장이 비어있거나 페이지 로드 문제일 수 있습니다.")
                # 이 경우, 사용자가 1페이지만 요청했다면 빈 파일이 생성되거나 파일이 안 만들어질 수 있음.
                # _extract_words_from_current_page에서 이미 로그를 남기고 빈 리스트를 반환함.
            
            all_data_for_csv.extend(page_csv_data) # 추출된 데이터 추가
            self._log_status(f"  {len(page_csv_data)}개의 단어 정보 추출 완료 (요청 페이지 {i}, 실제 페이지 {self.current_selenium_page}).")

            if i == num_pages: # 사용자가 요청한 마지막 페이지에 도달했다면 루프 종료
                self._log_status("사용자가 요청한 모든 페이지 수만큼의 데이터 추출을 시도했습니다.")
                break

            # 다음 페이지로 이동 (마지막 요청 페이지가 아니라면)
            if not self._navigate_to_next_page():
                self._log_status("더 이상 다음 페이지로 이동할 수 없거나 오류 발생. 추출을 중단합니다.")
                break # 다음 페이지 이동 실패 시 루프 종료
            
        # CSV 파일 저장
        if all_data_for_csv:
            csv_headers = ["히라가나", "한자", "품사", "뜻", "예문", "메모"] 
            self._log_status(f"총 {len(all_data_for_csv)}개의 단어 정보를 CSV 파일에 저장합니다...")
            try:
                with open(output_filepath, 'w', newline='', encoding='utf-8-sig') as csvfile: # utf-8-sig로 Excel 호환성 높임
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerow(csv_headers) # 헤더 작성
                    csv_writer.writerows(all_data_for_csv) # 데이터 행들 작성
                self._log_status(f"CSV 파일 저장 완료: {output_filepath}")
            except IOError as e:
                self._log_status(f"파일 저장 중 오류 발생: {e}")
                messagebox.showerror("파일 저장 오류", f"파일 저장 중 오류가 발생했습니다: {output_filepath}\n{e}")
        else:
            self._log_status("추출된 단어가 없어 파일을 저장하지 않습니다.")


    def quit_driver(self):
        """WebDriver를 종료합니다."""
        if self.driver:
            self._log_status("WebDriver를 종료합니다.")
            try:
                self.driver.quit()
            except Exception as e: # 드라이버 종료 중 발생할 수 있는 예외 처리
                self._log_status(f"WebDriver 종료 중 오류 발생: {e}")
            finally:
                self.driver = None # 드라이버 참조 제거