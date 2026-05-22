from playwright.sync_api import sync_playwright
import time
import csv
from collections import Counter

def scrape_kakaopage_tags():
    output_file = "kakaopage_tags_sample.csv"
    

    with sync_playwright() as p:
        # 1. 브라우저 열기 (headless=False 로 설정하여 스크롤되는 과정을 눈으로 확인)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # [수정 필요 1] 카카오페이지 실시간 랭킹 주소를 넣어주세요.
        target_url = "https://page.kakao.com/menu/10011/screen/94"
        page.goto(target_url)
        page.wait_for_timeout(2000) # 처음 접속 시 기본 로딩 대기 (2초)

        # 2. 회원님 아이디어 적용: 시간 기반 무한 스크롤
        print("작품 목록을 불러오기 위해 스크롤을 시작합니다...")
        scroll_duration = 25  # 300개를 불러오기 위해 스크롤 시간을 넉넉히 둡니다.
        end_time = time.time() + scroll_duration

        while time.time() < end_time:
            # 키보드의 'Page Down' 키를 눌러서 화면을 내립니다. (사람과 가장 흡사한 방식)
            page.keyboard.press('PageDown')
            time.sleep(1) # 너무 빠르게 누르면 로딩을 못 따라가므로 약간의 텀을 줌

        # 3. 로드된 작품들의 URL 수집 (회원님이 찾으신 완벽한 셀렉터 적용)
        item_selector = "a[href^='/content/']"
        items = page.query_selector_all(item_selector)
        
        urls = []
        for item in items:
            link = item.get_attribute("href")
            full_url = f"https://page.kakao.com{link}"
            
            # 정보 탭으로 바로가는 '?tab_type=about' 강제 추가 (클릭 생략용)
            if "tab_type=about" not in full_url:
                full_url += "&tab_type=about" if "?" in full_url else "?tab_type=about"
                
            urls.append(full_url)

        # 수집된 URL 중 혹시 모를 중복 제거 (랭킹 순서 유지)
        urls = list(dict.fromkeys(urls)) 
        print(f"총 {len(urls)}개의 작품 상세 페이지 주소 수집 완료!")
        print("태그 수집을 시작합니다...")

        tags_data = []

       
       # 4. 각 상세 페이지 접속 및 태그 수집
        for i, url in enumerate(urls, 1):
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(2000) 
                
                # 정보 탭 클릭 시도
                try:
                    page.get_by_text("정보", exact=True).click(timeout=3000)
                except:
                    pass 
                
                # 🌟 [개선 포인트 1] 여유로운 대기 시간 (1초 -> 3초)
                page.wait_for_timeout(3000)

                # ========================================================
                # 🌟 [새로운 퀘스트] 작품 제목 추출하기!
                try:
                    # 눈에 보이는 h2 디자인 태그 대신, 웹페이지 뒷면에 고정된 진짜 제목을 가져옵니다.
                    title_text = page.locator("meta[property='og:title']").get_attribute("content")
                    
                    # 보통 "나 혼자만 레벨업 - 카카오페이지" 처럼 뒤에 꼬리표가 붙으므로 깔끔하게 떼어줍니다.
                    if title_text and " - 카카오페이지" in title_text:
                        title_text = title_text.replace(" - 카카오페이지", "")
                        
                    title_text = title_text.strip()
                    
                except Exception as e:
                    # 만약 여기서도 에러가 난다면 진짜 원인을 출력해 줍니다.
                    title_text = "제목 확인 불가"
                    print(f"[{i}] 제목 추출 에러 상세 원인: {e}")
                # ========================================================

                # 태그 찾기
                tag_locator = page.locator("span", has_text="#")
                tag_count = tag_locator.count()

                if tag_count == 0:
                    print(f"[{i}/{len(urls)}] '{title_text}' 태그 후보를 찾지 못했습니다.")
                    continue

                work_tags = []
                for tag_index in range(tag_count):
                    tag_text = tag_locator.nth(tag_index).inner_text().strip()
                    
                    # 🌟 [개선 포인트 2] 진짜 태그만 가져오는 깐깐한 조건!
                    if tag_text.startswith("#") and " " not in tag_text and len(tag_text) < 15:
                        if tag_text not in work_tags:
                            work_tags.append(tag_text)
                
                # 데이터 바구니에 'title(제목)' 도 같이 담아줍니다.
                tags_data.append({"rank": i, "title": title_text, "tags": work_tags})
                print(f"[{i}/{len(urls)}] 수집 성공: {title_text} | {work_tags}")
                
            except Exception as e:
                print(f"[{i}/{len(urls)}] 수집 패스 (에러 원인: {e})")
                continue 
        
        # 5. 수집 종료 및 브라우저 닫기
        browser.close()
        
        # 6. CSV 파일로 예쁘게 저장하기
        with open(output_file, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["순위", "제목", "태그"]) 
            
            for row in tags_data:
                writer.writerow([row["rank"], row["title"], ", ".join(row["tags"])])

            tag_counts = Counter()
            for row in tags_data:
                tag_counts.update(row["tags"])

            writer.writerow([])
            writer.writerow(["태그", "합계"])
            for tag, count in tag_counts.most_common():
                writer.writerow([tag, count])

        print(f"CSV 저장 완료: {output_file}")
        print("\n🎉 모든 수집이 완료되었습니다!")
        return tags_data
# 함수 실행
if __name__ == "__main__":
    scrape_kakaopage_tags()