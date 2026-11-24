// 그림책 사이트(storybooks.dhammadana.kr) 방문 통계 — 도서관 /admin/stats/ 의 '그림책 사이트' 칸에 따로 모임 (운영자 요청, 2026-11-24)
// 그림책 사이트의 모든 페이지 </body> 앞에 한 줄: <script src="https://dhammadana.kr/assets/sbhit.js" defer></script>
// 보내는 것: 화면 주소·제목·들어온 사이트·기기마다 무작위 번호뿐 (이름·IP·이메일은 보내지 않음).
// 관리자 기기 빼기: 그 기기에서 https://storybooks.dhammadana.kr/?dd-notrack=1 을 한 번 열면 그 뒤로 보내지 않음(?dd-notrack=0 이면 다시 셈).
(function () {
  try {
    if (location.protocol !== 'https:' || !navigator.sendBeacon) return;
    var BOT = /bot|crawl|spider|slurp|preview|headless|lighthouse/i;
    if (BOT.test(navigator.userAgent || '')) return;
    var q = new URLSearchParams(location.search);
    if (q.has('dd-notrack')) localStorage.setItem('dd-notrack', q.get('dd-notrack') === '0' ? 'false' : 'true');
    if (localStorage.getItem('dd-notrack') === 'true') return;
    var v = localStorage.getItem('dd-sbvid') || '';
    if (!/^[0-9a-z]{8,24}$/.test(v)) { v = Math.random().toString(36).slice(2, 12) + Date.now().toString(36).slice(-4); localStorage.setItem('dd-sbvid', v); }
    var last = '', ref = document.referrer;
    var send = function () {
      var p = location.pathname + (/^#[!\/]/.test(location.hash) ? location.hash.replace(/[?].*$/, '') : '');
      if (p === last) return; last = p;
      setTimeout(function () {  // 제목이 바뀐 뒤에 보냄
        navigator.sendBeacon('https://dhammadana.kr/api/hit', JSON.stringify({ p: p.slice(0, 200), t: document.title, r: ref, v: v }));
        ref = '';
      }, 400);
    };
    send();
    // 페이지를 새로 열지 않고 화면만 바뀌는 사이트도 셈
    ['pushState', 'replaceState'].forEach(function (m) {
      var f = history[m]; if (!f) return;
      history[m] = function () { var r = f.apply(this, arguments); setTimeout(send, 0); return r; };
    });
    addEventListener('popstate', send); addEventListener('hashchange', send);
  } catch (e) {}
})();
