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

})();
