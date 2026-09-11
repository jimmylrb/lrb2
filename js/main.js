/* 二伯杀毒官网 — 交互脚本 */
(function(){
  'use strict';

  /* ---------- 移动端导航 ---------- */
  var navToggle = document.getElementById('navToggle');
  var navLinks = document.querySelector('.nav-links');
  if (navToggle) {
    navToggle.addEventListener('click', function(){
      navLinks.classList.toggle('open');
    });
    navLinks.querySelectorAll('a').forEach(function(a){
      a.addEventListener('click', function(){ navLinks.classList.remove('open'); });
    });
  }

  /* ---------- 导航滚动阴影 ---------- */
  var nav = document.getElementById('nav');
  window.addEventListener('scroll', function(){
    if (window.scrollY > 10) nav.classList.add('scrolled');
    else nav.classList.remove('scrolled');
  });

  /* ---------- 数字滚动动画 ---------- */
  function animateCount(el){
    var target = parseInt(el.getAttribute('data-target'), 10) || 0;
    var duration = 1400;
    var start = null;
    function step(ts){
      if (!start) start = ts;
      var p = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - p, 3); /* easeOutCubic */
      el.textContent = Math.round(target * eased).toLocaleString('en-US');
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  var io = new IntersectionObserver(function(entries){
    entries.forEach(function(en){
      if (en.isIntersecting){
        en.target.querySelectorAll('.count').forEach(animateCount);
        io.unobserve(en.target);
      }
    });
  }, { threshold: 0.4 });

  document.querySelectorAll('.hero-stats, .db-panel, .mini-cards').forEach(function(scope){
    io.observe(scope);
  });

  /* ---------- 界面模拟：侧边栏切换 ---------- */
  var sideItems = document.querySelectorAll('.side-item');
  var pages = document.querySelectorAll('.app-main .page');
  sideItems.forEach(function(btn){
    btn.addEventListener('click', function(){
      sideItems.forEach(function(b){ b.classList.remove('active'); });
      btn.classList.add('active');
      var target = 'page-' + btn.getAttribute('data-page');
      pages.forEach(function(p){ p.classList.toggle('active', p.id === target); });
    });
  });

  /* ---------- 扫描进度条动画（进入视口时） ---------- */
  var barObserver = new IntersectionObserver(function(entries){
    entries.forEach(function(en){
      if (en.isIntersecting){
        var i = en.target.querySelector('.scan-bar i');
        if (i) i.style.width = '68%';
        barObserver.unobserve(en.target);
      }
    });
  }, { threshold: 0.3 });
  var scanWrap = document.querySelector('.scan-bar-wrap');
  if (scanWrap){
    scanWrap.querySelector('.scan-bar i').style.width = '0%';
    barObserver.observe(scanWrap);
  }

  /* ---------- 终端打字机效果 ---------- */
  var lines = document.querySelectorAll('.terminal-body p');
  var tIdx = 0;
  lines.forEach(function(p){
    var full = p.textContent;
    p.setAttribute('data-full', full);
    p.textContent = '';
  });
  function typeNext(){
    if (tIdx >= lines.length) return;
    var p = lines[tIdx];
    var full = p.getAttribute('data-full');
    var i = 0;
    var timer = setInterval(function(){
      p.textContent = full.slice(0, ++i);
      if (i >= full.length){ clearInterval(timer); tIdx++; setTimeout(typeNext, 120); }
    }, 14);
  }
  setTimeout(typeNext, 600);


  /* ---------- 数据修改拦截演示 ---------- */
  var gLog = document.getElementById('guardLog');
  var gProg = document.getElementById('gProg');
  var gPath = document.getElementById('gPath');
  var gBlock = document.getElementById('gBlock');
  var gAllow = document.getElementById('gAllow');
  var gRestore = document.getElementById('gRestore');
  var gRetry = document.getElementById('gRetry');
  var gTrustChip = document.getElementById('gTrustChip');
  var gAlert = document.querySelector('.guard-alert');

  if (gLog && gProg){
    var guardAttacks = [
      { prog:'unknown.exe', path:'C:\\Users\\you\\Documents\\期末论文.docx', kind:'修改' },
      { prog:'sweeper.exe', path:'C:\\Users\\you\\Pictures\\毕业照.jpg', kind:'删除' },
      { prog:'rename.exe', path:'C:\\Users\\you\\Downloads\\报表.xlsx', kind:'改名' },
      { prog:'hacktool.dll', path:'C:\\Users\\you\\AppData\\Roaming\\config.ini', kind:'修改' },
      { prog:'loader.exe', path:'C:\\Users\\you\\Desktop\\账号密码.txt', kind:'修改' }
    ];
    var guardIdx = 0;
    var guardTrusted = 0;
    var gSimActive = true;

    function gAddLine(text, cls){
      var p = document.createElement('p');
      if (cls) p.className = cls;
      p.textContent = text;
      gLog.appendChild(p);
      gLog.scrollTop = gLog.scrollHeight;
    }
    function gSimulateAttack(){
      var a = guardAttacks[guardIdx % guardAttacks.length];
      guardIdx++;
      gProg.textContent = a.prog;
      gPath.textContent = a.path;
      gAlert.classList.remove('g-done');
      gAlert.style.opacity = '1';
      gSimActive = true;
      gAddLine('⚠️ ' + a.prog + ' 尝试' + a.kind + '数据 → ' + a.path, 'gl-warn');
      gAddLine('🛡️ 二伯杀毒实时拦截，原文件已自动备份到 .erbai-guard/backup/', 'gl-bad');
      gAddLine('📌 等待用户选择：信任并放行 / 继续拦截 / 回滚恢复', 'gl-cyan');
    }
    function gSetDone(msg, cls){
      gAlert.classList.add('g-done');
      gSimActive = false;
      gAddLine(msg, cls);
    }
    gBlock.addEventListener('click', function(){
      if (!gSimActive) return;
      gSetDone('⛔ 已继续拦截：保持文件原样，可疑程序已记录在案', 'gl-bad');
    });
    gAllow.addEventListener('click', function(){
      if (!gSimActive) return;
      guardTrusted++;
      gTrustChip.textContent = '信任区：' + guardTrusted + ' 项';
      gSetDone('✓ 已信任并放行：' + gProg.textContent + ' 已加入信任区，之后不再拦截', 'gl-ok');
    });
    gRestore.addEventListener('click', function(){
      if (!gSimActive) return;
      gSetDone('↩ 已回滚恢复：已从自动备份还原原始文件', 'gl-cyan');
    });
    gRetry.addEventListener('click', function(){
      gSimulateAttack();
    });
    gSimulateAttack();
  }

  /* ==========================================================
     受保护下载：半透明按钮 + 密码门
     ----------------------------------------------------------
     配置：改 VAULT 里的 url / filename / passHash 即可。
     新增密码摘要的算法见文件末尾注释。
     ========================================================== */
  var VAULT = {
    /* 主下载地址（GitHub 原站）。187 MB 超过 GitHub 单文件 100 MB 限制，
       不能走 Pages，放到 Releases（单文件上限 2 GB）。
       ⚠️ 资产名必须是纯 ASCII —— GitHub 会静默剥离资产名里的非 ASCII 字符，
          所以原文件名 "csv1.6中文版.exe" 的中文部分会被吃掉。 */
    url: 'https://github.com/jimmylrb/lrb2/releases/download/v1.6/csv1.6-CN.exe',
    /* 国内加速前缀：拼在原站地址前面走镜像中转。
       实测国内直连原站 29–67 KB/s（187 MB 要约 60 分钟），
       经此镜像 0.5–3.5 MB/s（约 1–7 分钟），且 206 支持断点续传、
       Content-Disposition 把文件名照常透传。
       ⚠️ 第三方公益服务，可能随时失效 —— 弹窗里常驻手动切换入口可回落到原站。
       留空字符串则只用原站。 */
    mirror: 'https://gh-proxy.com/',
    /* 保存到本地的文件名。跨域时浏览器会忽略本属性，实际文件名由服务端
       Content-Disposition 决定（= 资产名），这里保持与之一致以免误导。 */
    filename: 'csv1.6-CN.exe',
    /* 访问密码的 SHA-256 摘要 —— 明文不写入源码，改密码见文件末尾说明 */
    passHash: '06ef2991800a07a401ab1f1e91b1d85f263e4cf14e3012783eb117e6d54bc45e',
    maxTries: 5,
    lockMs: 30000
  };

  /* ---------- SHA-256：优先 WebCrypto，非安全上下文回退纯 JS ---------- */
  function utf8Bytes(str){
    var out = [], i, c;
    for (i = 0; i < str.length; i++){
      c = str.charCodeAt(i);
      if (c < 0x80) out.push(c);
      else if (c < 0x800) out.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f));
      else if (c >= 0xd800 && c <= 0xdbff){
        var c2 = str.charCodeAt(++i);
        c = 0x10000 + ((c - 0xd800) << 10) + (c2 - 0xdc00);
        out.push(0xf0 | (c >> 18), 0x80 | ((c >> 12) & 0x3f), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f));
      } else if (c >= 0xdc00 && c <= 0xdfff){
        out.push(0xef, 0xbf, 0xbd);
      } else {
        out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f));
      }
    }
    return out;
  }

  function sha256Pure(str){
    var K = [
      0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
      0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
      0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
      0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
      0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
      0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
      0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
      0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    ];
    var H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
    var msg = utf8Bytes(str);
    var l = msg.length;
    var bitHi = Math.floor(l / 536870912);
    var bitLo = (l << 3) >>> 0;
    msg.push(0x80);
    while (msg.length % 64 !== 56) msg.push(0);
    msg.push((bitHi >>> 24) & 0xff, (bitHi >>> 16) & 0xff, (bitHi >>> 8) & 0xff, bitHi & 0xff);
    msg.push((bitLo >>> 24) & 0xff, (bitLo >>> 16) & 0xff, (bitLo >>> 8) & 0xff, bitLo & 0xff);

    var w = new Array(64);
    function rr(x, n){ return (x >>> n) | (x << (32 - n)); }

    for (var off = 0; off < msg.length; off += 64){
      var i;
      for (i = 0; i < 16; i++){
        w[i] = ((msg[off + i*4] << 24) | (msg[off + i*4+1] << 16) | (msg[off + i*4+2] << 8) | msg[off + i*4+3]) | 0;
      }
      for (i = 16; i < 64; i++){
        var s0 = rr(w[i-15], 7) ^ rr(w[i-15], 18) ^ (w[i-15] >>> 3);
        var s1 = rr(w[i-2], 17) ^ rr(w[i-2], 19) ^ (w[i-2] >>> 10);
        w[i] = (w[i-16] + s0 + w[i-7] + s1) | 0;
      }
      var a = H[0], b = H[1], c = H[2], d = H[3], e = H[4], f = H[5], g = H[6], h = H[7];
      for (i = 0; i < 64; i++){
        var S1 = rr(e, 6) ^ rr(e, 11) ^ rr(e, 25);
        var ch = (e & f) ^ (~e & g);
        var t1 = (h + S1 + ch + K[i] + w[i]) | 0;
        var S0 = rr(a, 2) ^ rr(a, 13) ^ rr(a, 22);
        var maj = (a & b) ^ (a & c) ^ (b & c);
        var t2 = (S0 + maj) | 0;
        h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
      }
      H[0] = (H[0] + a) | 0; H[1] = (H[1] + b) | 0; H[2] = (H[2] + c) | 0; H[3] = (H[3] + d) | 0;
      H[4] = (H[4] + e) | 0; H[5] = (H[5] + f) | 0; H[6] = (H[6] + g) | 0; H[7] = (H[7] + h) | 0;
    }
    return H.map(function(x){ return ('00000000' + (x >>> 0).toString(16)).slice(-8); }).join('');
  }

  function sha256Hex(str){
    if (window.crypto && window.crypto.subtle && window.crypto.subtle.digest && window.TextEncoder){
      try {
        var buf = new TextEncoder().encode(str);
        return window.crypto.subtle.digest('SHA-256', buf).then(function(ab){
          var b = new Uint8Array(ab), s = '';
          for (var i = 0; i < b.length; i++) s += ('0' + b[i].toString(16)).slice(-2);
          return s;
        });
      } catch (e){ /* 回退到纯 JS */ }
    }
    return Promise.resolve(sha256Pure(str));
  }

  /* ---------- 密码门逻辑 ---------- */
  window.lrbSha256 = sha256Hex; /* 便于在控制台为新密码生成摘要 */
  var vModal = document.getElementById('vaultModal');
  if (vModal){
    var vDialog = vModal.querySelector('.vault-dialog');
    var vBtn = document.getElementById('vaultBtn');
    var vClose = document.getElementById('vaultClose');
    var vCancel = document.getElementById('vaultCancel');
    var vSubmit = document.getElementById('vaultSubmit');
    var vPass = document.getElementById('vaultPass');
    var vMsg = document.getElementById('vaultMsg');
    var vEye = document.getElementById('vaultEye');
    var vTries = 0;
    var vLockUntil = 0;

    function vSetMsg(text, cls){
      vMsg.textContent = text || '';
      vMsg.className = 'vault-msg' + (cls ? ' ' + cls : '');
    }
    function vShake(){
      vDialog.classList.remove('shake');
      void vDialog.offsetWidth; /* 强制重排以重启动画 */
      vDialog.classList.add('shake');
      setTimeout(function(){ vDialog.classList.remove('shake'); }, 460);
    }
    function vOpenModal(){
      vModal.classList.add('open');
      vModal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('vault-body-lock');
      vPass.value = '';
      vPass.type = 'password';
      vEye.textContent = '👁';
      vSetMsg('');
      vShowAlt(false);
      setTimeout(function(){ vPass.focus(); }, 60);
    }
    function vCloseModal(){
      vModal.classList.remove('open');
      vModal.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('vault-body-lock');
      vPass.value = '';
      vPass.type = 'password';
      vEye.textContent = '👁';
    }
    function vStartLock(){
      vLockUntil = Date.now() + VAULT.lockMs;
      vSubmit.disabled = true;
      vPass.disabled = true;
      (function tick(){
        var left = Math.ceil((vLockUntil - Date.now()) / 1000);
        if (left > 0){
          vSetMsg('⛔ 尝试次数过多，请等待 ' + left + ' 秒', 'err');
          setTimeout(tick, 250);
        } else {
          vTries = 0;
          vSubmit.disabled = false;
          vPass.disabled = false;
          vSetMsg('');
        }
      })();
    }
    var vAltWrap = document.getElementById('vaultAlt');
    var vAltLink = document.getElementById('vaultAltLink');

    function vShowAlt(show){
      if (vAltWrap) vAltWrap.hidden = !show;
    }
    /* 真正触发下载。useMirror 为真且配了镜像前缀时走加速通道。 */
    function vFireDownload(useMirror){
      var viaMirror = !!(useMirror && VAULT.mirror);
      var a = document.createElement('a');
      a.href = viaMirror ? (VAULT.mirror + VAULT.url) : VAULT.url;
      a.setAttribute('download', VAULT.filename);
      a.rel = 'noopener';
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      vShowAlt(true);
      setTimeout(function(){
        vSetMsg('📦 已通过' + (viaMirror ? '国内加速通道' : ' GitHub 原站') +
                '开始下载 · 178.8 MB，若被浏览器拦截请允许本站下载', 'cyan');
      }, 1000);
    }
    /* 直接走加速通道，不做前置探测。
       ------------------------------------------------------------
       为什么不做探测：实测镜像的 HEAD 要 1816 ms 才响应（Cloudflare 回源），
       而探测的用意是「1.2 秒没答复就当它挂了」—— 结果每次都被误判成挂了，
       所有人被静默降级回原站，等于白加加速通道。
       通道选择交给用户：下载开始后弹窗里常驻「改用 GitHub 原站」入口。 */
    function vStartDownload(){
      vFireDownload(true);   /* mirror 为空时 vFireDownload 内部自动走原站 */
    }
    function vVerify(){
      if (Date.now() < vLockUntil) return;
      var val = vPass.value;
      if (!val){
        vShake();
        vSetMsg('请输入访问密码', 'err');
        vPass.focus();
        return;
      }
      vSubmit.disabled = true;
      vSetMsg('校验中…');
      sha256Hex(val).then(function(h){
        vSubmit.disabled = false;
        if (h === VAULT.passHash){
          vTries = 0;
          vPass.value = '';
          vSetMsg('✅ 密码正确，正在开始下载…', 'ok');
          vStartDownload();
        } else {
          vTries++;
          vShake();
          vPass.select();
          if (vTries >= VAULT.maxTries){
            vStartLock();
          } else {
            vSetMsg('❌ 密码错误，还可尝试 ' + (VAULT.maxTries - vTries) + ' 次', 'err');
          }
        }
      }).catch(function(){
        vSubmit.disabled = false;
        vSetMsg('⚠️ 当前环境不支持密码校验，请通过 http(s) 访问本页', 'warn');
      });
    }

    vBtn.addEventListener('click', vOpenModal);
    if (vAltLink){
      vAltLink.addEventListener('click', function(e){
        e.preventDefault();
        vFireDownload(false);
      });
    }
    vClose.addEventListener('click', vCloseModal);
    vCancel.addEventListener('click', vCloseModal);
    vSubmit.addEventListener('click', vVerify);
    vEye.addEventListener('click', function(){
      var show = vPass.type === 'password';
      vPass.type = show ? 'text' : 'password';
      vEye.textContent = show ? '🙈' : '👁';
      vPass.focus();
    });
    vPass.addEventListener('keydown', function(e){
      if (e.key === 'Enter' || e.keyCode === 13) vVerify();
    });
    vModal.addEventListener('click', function(e){
      if (e.target.getAttribute && e.target.getAttribute('data-close') !== null) vCloseModal();
    });
    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape' && vModal.classList.contains('open')) vCloseModal();
    });
  }

})();

/* ----------------------------------------------------------
   改密码后重新生成摘要（在任意已加载本页的控制台执行）：
   lrbSha256('新密码').then(console.log)
   把结果填回 VAULT.passHash 即可。
   ---------------------------------------------------------- */
