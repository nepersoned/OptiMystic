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
  var html = HtmlService.createHtmlOutputFromFile('Sidebar')
    .setTitle('OptiMystic')
    .setWidth(360);
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
