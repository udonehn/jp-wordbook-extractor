import os
from bs4 import BeautifulSoup
num=int(input("총 페이지 수? "))   #페이지 수 설정

file = open(os.path.join(os.path.expanduser('~'),'Desktop\\')+'word_anki.txt', 'w',encoding='UTF-8')  #저장할 파일 열기 (바탕화면)
for i in range(num):    #페이지 수 만큼 실행
    html = open(os.path.join(os.path.expanduser('~'),'Desktop\\')+str(i+1)+'.html', 'r', encoding='utf-8').read()     #html 파일 열기 (바탕화면)

    soup = BeautifulSoup(html,'html.parser')    #html parser 실행
    divs = soup.findAll('div', 'inner_card')    #단어 목록을 div단위로 추출 (한 페이지에 20개)

    for div in divs:
        word = div.find('a').get_text().replace('\n','').replace('	','').replace('-','')   #단어를 찾아 텍스트 추출, 엔터 제거, 공백 제거, 하이픈 제거 (한자와 히라가나를 모두 추출)
        if '[' in word: #괄호가 있다면 실행(한자가 있다면 실행)
            file.write(word.split('[')[0]+'\t') #히라가나 추출 #('['를 경계로 히라가나와 한자 분리)
            file.write(word.split('[')[1].replace(']','')+'\t')  #한자 추출, '[' 제거
        else:   #괄호가 없다면 실행
            file.write(word+'\t'+word+'\t')
        
        meanings = div.findAll('div', 'mean_desc') #단어의 모든 뜻 찾기, div태그이면서 mean_desc 클래스
        for meaning in meanings:
            if meaning.em is not None: #값이 none이 아니라면 실행
                meaning.em.decompose() #em 태그 제거  
            file.write(meaning.get_text().replace('\n',"").replace('	',"")+'<br>') #뜻에서 텍스트 추출, 엔터 제거, 공백(탭?)제거 + 줄바꿈
            
        file.write('\t')
        
        exams = div.findAll('li','item_example')    #단어의 모든 예문 찾기
        for exam in exams:
            origin = exam.find('p','origin')    #예문 추출
            file.write(origin.get_text().replace('\n',"").replace('	',"")+'<br>') 
            translate = exam.find('p','translate')  #예문 해석 추출
            file.write(translate.get_text().replace('\n',"").replace('	',"")+'<br><br>')

        file.write('\n')
        
file.close()

"""
# ja.dict_wordbook_to_anki
네이버 일본어 단어장 Anki 가져오기 파일로 추출

Anki에 단어를 일일히 추가하는 것이 힘들어 만들었습니다.
단어장에 등록해 놓은 단어를 추출해 한자, 가나, 뜻, 예문 4가지 필드로 정리합니다.

# 사용법
1. 네이버 일본어 단어장 각 페이지를 우클릭-> 다른이름으로 저장을 눌러 html 파일을 바탕화면에 저장합니다.
2. html파일의 이름을 1부터 시작해 숫자로 저장합니다. (예를 들어 1.html, 2.html...)
3. 파일을 실행해 최대 몇 페이지까지 있는지 입력합니다. (예를 들어 2 페이지라면 2라고 입력)
4. 바탕화면에 생성된 word_anki.txt 파일을 Anki의 가져오기를 통해 불러옵니다.
5. 4개의 필드를 적당히 배정합니다.
"""