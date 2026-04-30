// OptiMystic Google Sheets Add-on
// Server-side Apps Script

var DEFAULT_BACKEND = 'https://optimystic-826180130763.asia-northeast3.run.app';

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('OptiMystic')
    .addItem('💬 Open Chat', 'openSidebar')
    .addSeparator()
    .addItem('⚙️ Settings', 'openSettings')
    .addToUi();
}

function openSidebar() {
  var tmpl = HtmlService.createTemplateFromFile('Sidebar');
  tmpl.token = ScriptApp.getOAuthToken();
  tmpl.spreadsheetId = SpreadsheetApp.getActiveSpreadsheet().getId();
  tmpl.sheetName = SpreadsheetApp.getActiveSheet().getName();
  var html = tmpl.evaluate().setTitle('OptiMystic').setWidth(360);
  SpreadsheetApp.getUi().showSidebar(html);
}

function openSettings() {
  var ui = SpreadsheetApp.getUi();
  var current = getBackendUrl();
  var result = ui.prompt(
    'OptiMystic Settings',
    'Backend URL:',
    ui.ButtonSet.OK_CANCEL
  );
  if (result.getSelectedButton() === ui.Button.OK) {
    var url = result.getResponseText().trim();
    if (url) {
      PropertiesService.getUserProperties().setProperty('BACKEND_URL', url);
      ui.alert('Saved! Backend: ' + url);
    }
  }
}

function getBackendUrl() {
  return PropertiesService.getUserProperties().getProperty('BACKEND_URL')
    || PropertiesService.getScriptProperties().getProperty('BACKEND_URL')
    || DEFAULT_BACKEND;
}

function loadSampleData() {
  var data = [
    ["주문번호","거래처명","지역","위도","경도","배송중량","수량(개)","배송가능시작","마감시간","우선순위","차량구분","작업시간(분)","주문금액","비고"],
    ["ORD-2401","삼성전자 서초사업장 (자재팀)","서초",37.4862,127.0328,"145.5kg",23,"09:00","12:00","A","트럭",25,3850000,""],
    ["ORD-2402","LG화학 마포사무소","마포",37.5539,126.9116,88.2,14,"8시30분","11:30","B","van",15,1240000,"냉장필요"],
    ["ORD-2403","현대자동차 강남지점","강남",37.4979,127.0276,210,31,"10:00","14:00","B","트럭",30,5200000,""],
    ["ORD-2404","SK하이닉스 판교R&D센터","성남","",127.1052,55.8,9,"1300","17:00","B","van",12,980000,"위도누락"],
    ["ORD-2405","카카오 판교아지트","판교",37.3948,"",32.4,6,"09:00","18:00","C","van",10,420000,"경도없음"],
    ["ORD-2406","롯데그룹 잠실타워 본사","송파",37.5145,127.1059,178.3,28,"0800","12:00","A","트럭",25,4100000,""],
    ["ORD-2407","포스코 강남타워","강남",37.5037,127.0244,95.6,15,"11:00","15:00","B","van",18,1680000,""],
    ["ORD-2408","KT 광화문지사 전산실","종로구",37.5704,126.9825,67.1,11,"8시30분","11:00","A","van",12,890000,""],
    ["ORD-2409","네이버 강남오피스","강남",37.4963,127.0285,41.2,7,"14:00","18:00","C","van",10,560000,""],
    ["ORD-2410","두산중공업 용산사업소","용산","","",302,45,"07:30","11:30","A","트럭",40,7800000,"좌표미확인"],
    ["ORD-2411","GS칼텍스 역삼영업소","강남",37.5005,127.0361,76.4,12,"10:00","13:00","B","van",15,1120000,""],
    ["ORD-2412","한화그룹 장교동 본사","중구",37.5632,126.9979,134.5,21,"0930","13:30","B","트럭",22,2900000,""],
    ["ORD-2413","CJ제일제당 마포사무소","마포",37.548,126.913,89.7,16,"08:00","12:00","A","van",18,1350000,""],
    ["ORD-2414","아모레퍼시픽 용산 신사옥","용산",37.5293,126.9641,55.3,10,"13:00","17:00","C","van",12,780000,""],
    ["ORD-2415","신세계백화점 강남점","서초",37.498,127.0276,420,60,"06:00","09:00","A","트럭",45,9200000,"새벽배송"],
    ["ORD-2416","현대백화점 압구정본점","강남",37.5272,127.0286,"315.8kg",48,"630","0930","A","트럭",40,8100000,"새벽배송"],
    ["ORD-2417","이마트 성수점 (식품팀)","성동",37.5448,127.0566,580,85,"05:00","08:00","A","트럭",60,12500000,""],
    ["ORD-2418","코스트코 양재점","서초",37.4685,127.0374,890,120,"04:30","0730","A","트럭",90,18900000,""],
    ["ORD-2419","홈플러스 영등포점","영등포",37.5264,126.8963,445,65,"05:30","08:30","A","트럭",55,9800000,""],
    ["ORD-2420","농심 신대방물류","동작",37.4988,126.9197,234.5,36,"09:00","13:00","B","트럭",30,4200000,""],
    ["ORD-2421","오리온 신촌영업소","서대문",37.5791,126.9368,112.3,18,"10:00","14:00","B","van",20,1560000,""],
    ["ORD-2422","빙그레 노원물류센터","노원",37.6541,127.0566,167.8,26,"08:00","12:00","B","트럭",25,2840000,""],
    ["ORD-2423","하이트진로 도봉창고","도봉",37.6688,127.0457,298.4,42,"07:00","11:00","A","트럭",35,5600000,""],
    ["ORD-2424","롯데칠성 은평지점","은평",37.6176,126.9227,198.6,30,"09:00","13:00","B","트럭",28,3200000,""],
    ["ORD-2425","CU편의점 강서물류","강서",37.5586,126.8366,75.2,14,"11:00","15:00","C","van",15,980000,""],
    ["ORD-2426","쿠팡 송파허브","송파",37.4836,127.1237,1240,180,"03:00","06:00","A","트럭",120,28400000,"새벽배송"],
    ["ORD-2427","마켓컬리 장지센터","송파",37.472,127.1384,980,145,"0200","05:00","A","트럭",100,22100000,"새벽배송"],
    ["ORD-2428","SSG닷컴 오금물류","송파",37.4978,127.1264,560,88,"04:00","07:00","A","트럭",70,13200000,""],
    ["ORD-2429","배달의민족 목동오피스","양천",37.5256,126.8759,28.5,5,"13:00","18:00","C","van",8,380000,""],
    ["ORD-2430","토스 강남센터","강남",37.504,127.0245,18.2,3,"10:00","17:00","C","van",8,240000,""]
  ];
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Sheet1') || ss.getSheets()[0];
  sheet.clearContents();
  sheet.getRange(1, 1, data.length, data[0].length).setValues(data);
  sheet.setName('korexpress_2401');
  return 'loaded ' + (data.length - 1) + ' rows';
}

function testSendChat() {
  var result = sendChat('hello', []);
  Logger.log(JSON.stringify(result));
}

// Debug: test backend connectivity
function pingBackend() {
  var backendUrl = getBackendUrl();
  try {
    var response = UrlFetchApp.fetch(backendUrl + '/sheets/chat', {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify({message: 'ping', headers: [], rows: [], sheet_name: 'Test', history: []}),
      muteHttpExceptions: true,
      deadline: 30
    });
    return 'OK ' + response.getResponseCode() + ': ' + response.getContentText().substring(0, 100);
  } catch(e) {
    return 'ERROR: ' + e.message;
  }
}

// Returns OAuth token + sheet info — backend reads data directly via Sheets API
function getSessionInfo() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getActiveSheet();
  return {
    token: ScriptApp.getOAuthToken(),
    spreadsheet_id: ss.getId(),
    sheet_name: sheet.getName()
  };
}

// Called from sidebar JS via google.script.run
function getSheetData() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var range = sheet.getDataRange();
  var values = range.getValues();
  if (!values || values.length === 0) {
    return { sheet_name: sheet.getName(), headers: [], rows: [] };
  }
  return {
    sheet_name: sheet.getName(),
    headers: values[0].map(String),
    rows: values.slice(1, 201)
  };
}

function sendChat(message, history) {
  var data = getSheetData();
  var backendUrl = getBackendUrl();

  var payload = JSON.stringify({
    message: message,
    sheet_name: data.sheet_name,
    headers: data.headers,
    rows: data.rows,
    history: history || []
  });

  var options = {
    method: 'post',
    contentType: 'application/json',
    payload: payload,
    muteHttpExceptions: true,
    deadline: 30
  };

  try {
    var response = UrlFetchApp.fetch(backendUrl + '/sheets/chat', options);
    var code = response.getResponseCode();
    if (code !== 200) {
      return { reply: 'Server error ' + code + ': ' + response.getContentText(), suggested_changes: null };
    }
    return JSON.parse(response.getContentText());
  } catch (e) {
    return { reply: 'Connection failed: ' + e.message, suggested_changes: null };
  }
}

function applyChanges(changes) {
  var sheet = SpreadsheetApp.getActiveSheet();
  // changes: [{row, col, value}] — row 0 = first data row (below header)
  changes.forEach(function(c) {
    sheet.getRange(c.row + 2, c.col + 1).setValue(c.value);
  });
  return { ok: true, count: changes.length };
}

function writeResultSheet(sheetName, headers, rows) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);
  if (sheet) {
    sheet.clear();
  } else {
    sheet = ss.insertSheet(sheetName);
  }
  if (headers && headers.length > 0) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    if (rows && rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    }
  }
  sheet.activate();
  return { ok: true };
}
