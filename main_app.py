import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
# from urllib.parse import quote # 현재 직접 사용하지 않으므로 주석 처리 또는 삭제
from crawler_module import NaverWordbookCrawler

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("네이버 단어장 크롤러")
        self.root.geometry("550x520")

        self.crawler = NaverWordbookCrawler(status_callback=self.update_status_thread_safe)
        # 기본 설정값들
        self.default_wordbook_name_gui = "단어"
        self.wordbook_main_url = "https://learn.dict.naver.com/wordbook/jakodict/#/my/main" # 네이버 단어장 목록 메인 페이지
        self.default_save_filename = "word_list.csv"

        # --- 메인 프레임 ---
        main_frame = ttk.Frame(root, padding="10 10 10 10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root.columnconfigure(0, weight=1) # 창 크기 변경 시 main_frame이 같이 늘어나도록
        root.rowconfigure(0, weight=1)

        # --- 1단계 UI: 브라우저 열기 버튼 ---
        # 사용자가 가장 먼저 상호작용하는 부분
        self.step1_frame = ttk.Frame(main_frame)
        self.step1_frame.grid(row=0, column=0, columnspan=3, sticky=tk.EW, pady=(0,10))
        self.open_browser_button = ttk.Button(self.step1_frame, text="1. 단어장 목록 열기 (로그인 필요)", command=self.open_main_page_for_login, width=40)
        self.open_browser_button.pack() # 프레임 내에서 가운데 정렬
        
        # --- 2단계 UI: 크롤링 옵션 입력 (초기에는 숨김) ---
        # 사용자가 브라우저를 열고 로그인 준비가 되면 이 부분이 나타남
        self.step2_options_frame = ttk.LabelFrame(main_frame, text="크롤링 옵션", padding="10 10 10 10")
        # self.step2_options_frame은 open_main_page_for_login 성공 시 grid로 표시됨

        # 대상 단어장 이름 입력 필드
        ttk.Label(self.step2_options_frame, text="대상 단어장 이름:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.wordbook_name_var = tk.StringVar(value=self.default_wordbook_name_gui)
        self.wordbook_name_entry = ttk.Entry(self.step2_options_frame, textvariable=self.wordbook_name_var, width=38)
        self.wordbook_name_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # 크롤링 할 페이지 수 입력 필드
        ttk.Label(self.step2_options_frame, text="크롤링 할 페이지 수:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.pages_entry = ttk.Entry(self.step2_options_frame, width=10)
        self.pages_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W) # 왼쪽 정렬
        
        # 저장 파일 이름 입력 필드
        ttk.Label(self.step2_options_frame, text="저장 파일 이름:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.save_filename_var = tk.StringVar(value=self.default_save_filename)
        self.save_filename_entry = ttk.Entry(self.step2_options_frame, textvariable=self.save_filename_var, width=38)
        self.save_filename_entry.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # 저장 폴더 선택 및 표시
        ttk.Label(self.step2_options_frame, text="저장 폴더:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.save_folder_var = tk.StringVar(value=os.getcwd()) # 기본값: 현재 작업 디렉토리
        self.save_folder_label = ttk.Label(self.step2_options_frame, textvariable=self.save_folder_var, relief="sunken", width=35, anchor=tk.W) # 선택된 폴더 경로 표시
        self.save_folder_label.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        self.select_folder_button = ttk.Button(self.step2_options_frame, text="폴더 선택...", command=self.select_save_folder, width=12)
        self.select_folder_button.grid(row=3, column=2, padx=5, pady=5)
        
        # 크롤링 시작 버튼
        self.start_crawling_button = ttk.Button(self.step2_options_frame, text="2. 단어장 선택 및 크롤링 시작", command=self.select_wordbook_and_start_crawling, width=40)
        self.start_crawling_button.grid(row=4, column=0, columnspan=3, pady=(10,0))
        
        self.step2_options_frame.columnconfigure(1, weight=1) # 입력 필드들이 가로 공간을 차지하도록

        # --- 로그 창 (항상 표시) ---
        ttk.Label(main_frame, text="진행 상황:").grid(row=2, column=0, columnspan=3, padx=5, pady=(10,2), sticky=tk.W)
        self.status_text = scrolledtext.ScrolledText(main_frame, width=60, height=10, state=tk.DISABLED, wrap=tk.WORD) # 읽기 전용, 자동 줄바꿈
        self.status_text.grid(row=3, column=0, columnspan=3, padx=5, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        main_frame.rowconfigure(3, weight=1) # 로그창이 세로 공간을 채우도록

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing) # 창 닫기 버튼 클릭 시 이벤트 처리
        
        # 초기 UI 상태: 2단계 옵션 프레임 숨기기
        self.step2_options_frame.grid_remove()

    def select_save_folder(self):
        """저장 폴더 선택 대화상자를 열고 사용자가 선택한 폴더 경로를 업데이트합니다."""
        # 현재 설정된 폴더를 초기 위치로 사용
        folder_selected = filedialog.askdirectory(initialdir=self.save_folder_var.get() or os.getcwd())
        if folder_selected: # 사용자가 폴더를 선택했다면
            self.save_folder_var.set(folder_selected)

    def update_status(self, message):
        """진행 상황 텍스트 영역에 메시지를 추가합니다. (GUI 스레드에서 직접 호출용)"""
        self.status_text.config(state=tk.NORMAL) # 편집 가능 상태로 변경
        self.status_text.insert(tk.END, message + "\n") # 메시지 추가
        self.status_text.see(tk.END) # 가장 최근 메시지가 보이도록 스크롤
        self.status_text.config(state=tk.DISABLED) # 다시 읽기 전용으로
        self.root.update_idletasks() # GUI 즉시 업데이트

    def update_status_thread_safe(self, message):
        """다른 스레드에서 GUI의 진행 상황을 안전하게 업데이트하기 위해 사용합니다."""
        self.root.after(0, self.update_status, message)

    def _set_ui_interaction_state(self, is_busy):
        """작업 중 여부에 따라 UI 요소들의 활성화/비활성화 상태를 설정합니다."""
        step1_button_state = tk.DISABLED if is_busy else tk.NORMAL
        step2_elements_state = tk.DISABLED if is_busy else tk.NORMAL
        
        self.open_browser_button.config(state=step1_button_state)
        
        # step2_options_frame이 화면에 표시된 경우에만 내부 요소 상태 변경
        if self.step2_options_frame.winfo_ismapped():
            for child in self.step2_options_frame.winfo_children():
                if isinstance(child, (ttk.Button, ttk.Entry)):
                    try:
                        child.config(state=step2_elements_state)
                    except tk.TclError: # 일부 위젯은 state 옵션이 없을 수 있음 (예: Label)
                        pass
            # 크롤링 시작 버튼은 드라이버가 있고, 작업 중이 아닐 때만 활성화
            self.start_crawling_button.config(state=tk.DISABLED if is_busy or not self.crawler.driver else tk.NORMAL)

    def open_main_page_for_login(self):
        """1단계: 브라우저를 열어 네이버 단어장 목록 메인 페이지로 이동하고, 사용자 로그인을 유도합니다."""
        self._set_ui_interaction_state(True) # 모든 주요 UI 상호작용 비활성화
        self.start_crawling_button.config(state=tk.DISABLED) # 크롤링 버튼은 아직

        self.status_text.config(state=tk.NORMAL) # 로그창 초기화
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.update_status("브라우저를 열고 단어장 목록 페이지로 이동합니다...")

        try:
            self.crawler.setup_driver_and_navigate(self.wordbook_main_url)
            self.update_status(f"브라우저가 열렸습니다. URL: {self.wordbook_main_url}")
            self.update_status("단어장 목록 페이지에서 네이버 로그인 및 2단계 인증을 완료해주세요.")
            self.update_status("완료 후 아래 옵션들을 입력하고 '2. 단어장 선택 및 크롤링 시작' 버튼을 눌러주세요.")
            
            # 2단계 UI 프레임 표시 및 내부 요소 활성화
            self.step2_options_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10, padx=2)
            self._set_ui_interaction_state(False) # 1단계 버튼은 비활성화, 2단계 옵션은 활성화
            self.open_browser_button.config(state=tk.DISABLED) # 브라우저 열기 버튼은 작업 완료 전까지 비활성화
            self.start_crawling_button.config(state=tk.NORMAL) # 크롤링 버튼 활성화

        except Exception as e:
            error_message = f"브라우저 열기 실패: {e}"
            self.update_status(error_message)
            messagebox.showerror("오류", error_message)
            self._set_ui_interaction_state(False) # 오류 시 UI 다시 활성화 (1단계 버튼 포함)

    def select_wordbook_and_start_crawling(self):
        """2단계: 사용자가 입력한 옵션을 바탕으로 특정 단어장을 선택하고 크롤링을 시작합니다."""
        wordbook_name_to_crawl = self.wordbook_name_var.get().strip()
        if not wordbook_name_to_crawl:
            messagebox.showerror("입력 오류", "대상 단어장 이름을 입력해주세요.")
            return

        num_pages_str = self.pages_entry.get()
        if not num_pages_str:
            messagebox.showerror("입력 오류", "크롤링 할 페이지 수를 입력해주세요.")
            return
        try:
            num_pages = int(num_pages_str)
            if num_pages <= 0:
                messagebox.showerror("입력 오류", "페이지 수는 1 이상이어야 합니다.")
                return
        except ValueError:
            messagebox.showerror("입력 오류", "페이지 수는 숫자로 입력해야 합니다.")
            return

        if not self.crawler.driver: # 드라이버가 설정되지 않았다면 (비정상적 상황)
            messagebox.showerror("오류", "브라우저가 열려있지 않습니다. '1. 단어장 목록 열기'를 먼저 실행해주세요.")
            return
            
        save_folder = self.save_folder_var.get()
        save_filename_input = self.save_filename_var.get().strip()
        if not save_folder:
            messagebox.showerror("입력 오류", "저장 폴더를 선택해주세요.")
            return
        if not save_filename_input:
            messagebox.showerror("입력 오류", "저장 파일 이름을 입력해주세요.")
            return
        
        # 파일 이름에 .csv 확장자 자동 추가
        if not save_filename_input.lower().endswith(".csv"):
            save_filename_input += ".csv"
            self.save_filename_var.set(save_filename_input) 
            
        output_filepath = os.path.join(save_folder, save_filename_input)

        self._set_ui_interaction_state(True) # 크롤링 중 모든 UI 비활성화

        # 백그라운드 스레드에서 크롤링 실행
        thread = threading.Thread(target=self.run_select_and_crawl_logic, 
                                  args=(wordbook_name_to_crawl, num_pages, output_filepath), 
                                  daemon=True) # 데몬 스레드로 메인 앱 종료 시 함께 종료
        thread.start()

    def run_select_and_crawl_logic(self, wordbook_name, num_pages, output_filepath):
        """백그라운드 스레드에서 실행될 실제 크롤링 로직입니다."""
        try:
            self.update_status_thread_safe(f"'{wordbook_name}' 단어장 선택 시도...")
            if self.crawler.select_wordbook(wordbook_name): # 단어장 선택
                self.update_status_thread_safe(f"'{wordbook_name}' 단어장 선택 완료. 크롤링을 시작합니다...")
                # 단어장 페이지에서 단어 크롤링
                self.crawler.crawl_wordbook_pages(
                    num_pages=num_pages,
                    output_filepath=output_filepath
                )
                filename_only = os.path.basename(output_filepath)
                success_message = f"크롤링 완료! {filename_only} 파일이 지정된 경로에 저장되었습니다."
                self.update_status_thread_safe(success_message)
                messagebox.showinfo("완료", success_message)
            else:
                # select_wordbook 메소드 내부에서 이미 실패 로그를 남겼을 것임
                messagebox.showerror("단어장 선택 실패", f"'{wordbook_name}' 단어장을 찾거나 접근할 수 없습니다. 이름을 확인해주세요.")
        except Exception as e:
            error_message = f"작업 중 오류 발생: {e}"
            self.update_status_thread_safe(error_message)
            messagebox.showerror("오류", error_message)
        finally:
            # 작업 완료 후 UI 상태 복원
            self.root.after(0, lambda: self._set_ui_interaction_state(False)) # 모든 관련 UI 요소들 다시 활성화
            # 크롤링 시작 버튼은 사용자가 다시 로그인을 하거나 브라우저가 열려있을 때만 활성화되도록 조건부 처리
            self.root.after(0, lambda: self.start_crawling_button.config(state=tk.DISABLED if not self.crawler.driver else tk.NORMAL))
            # 1단계 버튼은 항상 다시 활성화 (새로운 작업 시작 가능)
            self.root.after(0, lambda: self.open_browser_button.config(state=tk.NORMAL))


    def on_closing(self):
        """프로그램 창을 닫을 때 호출됩니다."""
        if messagebox.askokcancel("종료 확인", "프로그램을 종료하시겠습니까? (실행 중인 브라우저도 닫힙니다)"):
            if self.crawler:
                self.crawler.quit_driver() # WebDriver 종료
            self.root.destroy() # Tkinter 창 종료

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()