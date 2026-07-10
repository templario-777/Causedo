addEventListener('fetch', function(e) { e.respondWith(handle(e.request)); });
async function handle(request) {
  var url = new URL(request.url);
  var cors = {'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET,POST,OPTIONS','Access-Control-Allow-Headers':'Content-Type'};
  if (request.method === 'OPTIONS') return new Response(null, {headers:cors, status:200});
  if (url.pathname === '/') {
    var html = "<!DOCTYPE html><html lang='es'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Trading Bot</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:Inter,sans-serif;background:#0a0e13;color:#e2e8f0;overflow:hidden;height:100vh}.container{display:flex;height:100vh}.sidebar{width:320px;background:#0f1318;border-right:1px solid #2a2e35;padding:24px;display:flex;flex-direction:column;gap:20px}.price-display{background:linear-gradient(135deg,rgba(59,130,246,0.1),rgba(139,92,246,0.1));border:1px solid rgba(59,130,246,0.2);border-radius:14px;padding:16px;display:flex;flex-direction:column;gap:4px}.price-display .symbol{font-size:12px;color:#9ba1a6}.price-display .price{font-size:28px;font-weight:700}.price-display .change{font-size:14px;font-weight:600}button{padding:14px 20px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);border:none;border-radius:10px;color:white;font-size:14px;font-weight:600;cursor:pointer;width:100%}.chart-container{flex:1}#tradingview_widget{width:100%;height:100%}.chat-container{margin-top:20px;display:flex;flex-direction:column;gap:8px}#chat-messages{height:200px;overflow-y:auto;padding:10px;background:#0a0e13;border:1px solid #2a2e35;border-radius:8px;font-size:13px}.chat-input{display:flex;gap:8px}#chat-input{flex:1;padding:10px;background:#0a0e13;border:1px solid #2a2e35;border-radius:8px;color:white;font-size:13px}#chat-send{padding:10px 16px;background:linear-gradient(135deg,#8b5cf6,#3b82f6);border:none;border-radius:8px;color:white;font-weight:600;cursor:pointer}</style></head><body><div class='container'><div class='sidebar'><h2>Trading Bot</h2><input type='text' id='symbol-input' value='BTCUSDT' style='padding:14px;background:#0a0e13;border:1px solid #2a2e35;border-radius:10px;color:white;font-size:14px;width:100%'><div class='price-display'><div class='symbol' id='price-symbol'>CARGANDO...</div><div class='price' id='current-price'>$--</div><div class='change' id='price-change'>--</div></div><button onclick='updateChart()'>Actualizar</button><div class='chat-container'><h3>AI Analysis</h3><div id='chat-messages'></div><div class='chat-input'><input type='text' id='chat-input' placeholder='Pregunta al analista...'><button id='chat-send'>Enviar</button></div></div></div><div class='chart-container'><div id='tradingview_widget'></div></div></div><script src='https://s3.tradingview.com/tv.js'></script><script>var PROXY='https://proxy1.d-perez9.workers.dev/?target=';var widget;function initWidget(s){if(widget)widget.remove();var t=s.indexOf('/')>-1?'BINANCE:'+s.replace('/',''):(s.indexOf(':')>-1?s:'BINANCE:'+s);widget=new TradingView.widget({width:'100%',height:'100%',symbol:t,interval:'5',timezone:'Etc/UTC',theme:'dark',style:'1',locale:'es',container_id:'tradingview_widget'})}function updateChart(){initWidget(document.getElementById('symbol-input').value);updatePriceDisplay()}async function updatePriceDisplay(){document.getElementById('current-price').textContent='$...';document.getElementById('price-change').textContent='CARGANDO...';var s=document.getElementById('symbol-input').value.replace('BINANCE:','').replace('/','').toUpperCase();document.getElementById('price-symbol').textContent=s;try{var r=await fetch(PROXY+encodeURIComponent('https://api.binance.com/api/v3/ticker/24hr?symbol='+s));if(r.ok){var d=await r.json();document.getElementById('current-price').textContent='$'+parseFloat(d.lastPrice).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:8});var c=parseFloat(d.priceChangePercent);var e=document.getElementById('price-change');e.textContent=(c>=0?'+':'')+c.toFixed(2)+'%';e.style.color=c>=0?'#22c55e':'#ef4444'}}catch(ex){document.getElementById('current-price').textContent='$ERROR'}}async function sendChat(){var msg=document.getElementById('chat-input').value.trim();if(!msg)return;var symbol=document.getElementById('symbol-input').value;addMessage('user',msg);document.getElementById('chat-input').value='';var r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg,symbol:symbol})});var d=await r.json();addMessage('ai',d.response||'Error')}}function addMessage(role,text){var div=document.createElement('div');div.style.marginBottom='8px';div.style.color=role==='user'?'#60a5fa':'#a5f3fc';div.textContent=(role==='user'?'Tú: ':'IA: ')+text;document.getElementById('chat-messages').appendChild(div);document.getElementById('chat-messages').scrollTop=document.getElementById('chat-messages').scrollHeight}document.getElementById('chat-send').onclick=sendChat;document.getElementById('chat-input').addEventListener('keypress',function(e){if(e.key==='Enter')sendChat();});initWidget('BINANCE:BTCUSDT');setInterval(updatePriceDisplay,30000);setTimeout(updatePriceDisplay,500)</script></body></html>";
    return new Response(html, {headers:{'Content-Type':'text/html;charset=UTF-8','Access-Control-Allow-Origin':'*'}});
  }
  if (url.pathname === '/api/chat' && request.method === 'POST') {
    try {
      var body = await request.json();
      var userMessage = body.message;
      var symbol = body.symbol || 'BTCUSDT';
      var currentDate = new Date().toLocaleDateString('es-ES',{day:'numeric',month:'long',year:'numeric'});
      var symbolClean = symbol.replace('BINANCE:','').replace('/','').replace(':','').toUpperCase();
      var proxyBase = 'https://proxy1.d-perez9.workers.dev/?target=';
      var marketData = null, klinesData = null;
      try {
        var marketRes = await fetch(proxyBase + encodeURIComponent('https://api.binance.com/api/v3/ticker/24hr?symbol=' + symbolClean));
        if (marketRes.ok) marketData = await marketRes.json();
        var klinesRes = await fetch(proxyBase + encodeURIComponent('https://api.binance.com/api/v3/klines?symbol=' + symbolClean + '&interval=5m&limit=50'));
        if (klinesRes.ok) klinesData = await klinesRes.json();
      } catch(e) {}
      var dataMessage = userMessage;
      if (marketData) {
        dataMessage = 'DATOS REALES: ' + symbolClean + ' PRECIO: $' + marketData.lastPrice + ' HIGH: $' + marketData.highPrice + ' LOW: $' + marketData.lowPrice + ' CAMBIO: ' + marketData.priceChangePercent + '% VOLUMEN: $' + marketData.quoteVolume;
        if (klinesData) { dataMessage += ' VELAS:'; for (var i=Math.max(0,klinesData.length-5);i<klinesData.length;i++) { var k=klinesData[i]; dataMessage += ' V'+(i-klinesData.length+6)+':C='+k[4]; } }
        dataMessage += ' PREGUNTA: ' + userMessage;
      }
      var systemPrompt = 'ANALISTA TECNICO TRADING. FECHA:' + currentDate + '. PRECIOS 2dec. RSI compra70+ venta30-. LONG stop abajo SHORT stop arriba. TP min 1:1.5. SENAL UNICA. RIESGO 1-2%.';
      var aiResponse = await callNvidiaAI([{role:'system',content:systemPrompt},{role:'user',content:dataMessage}]);
      return new Response(JSON.stringify({response:aiResponse}), {headers:{'Content-Type':'application/json','Access-Control-Allow-Origin':'*'}});
    } catch(e) {
      return new Response(JSON.stringify({error:e.message}), {status:500, headers:{'Content-Type':'application/json','Access-Control-Allow-Origin':'*'}});
    }
  }
  return new Response('Not Found', {status:404, headers:cors});
}
async function callNvidiaAI(messages) {
  try {
    var apiKey = typeof NVIDIA_API_KEY !== 'undefined' ? NVIDIA_API_KEY : '';
    if (!apiKey) return 'NVIDIA_API_KEY not configured in Worker secrets';
    var response = await fetch('https://integrate.api.nvidia.com/v1/chat/completions', {
      method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer ' + apiKey},
      body:JSON.stringify({model:'meta/llama-3.1-8b-instruct',messages:messages,temperature:0.7,max_tokens:1500})
    });
    if (response.ok) { var result = await response.json(); return result.choices[0].message.content; }
    return 'NVIDIA API error: ' + response.status;
  } catch(e) { return 'Error: ' + e.message; }
}