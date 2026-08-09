// 二伯AI C++ 接入示例（Windows / MSVC + WinHTTP）
// 用途：把 AI 能力插入 C++ 软件（如 ErBaiAV 杀毒引擎）
//
// 编译（需要 Visual Studio Build Tools，x64 Native Tools 命令行）：
//   cl /EHsc demo_cpp.cpp /link winhttp.lib
// 运行：
//   demo_cpp.exe "检测到疑似勒索软件：尝试连接tor节点并加密磁盘"
#include <windows.h>
#include <winhttp.h>
#include <algorithm>
#include <cstdio>
#include <string>
#pragma comment(lib, "winhttp.lib")

static std::wstring to_wide(const std::string& s) {
  if (s.empty()) return L"";
  int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, nullptr, 0);
  std::wstring w(n - 1, L'\0');
  MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, &w[0], n);
  return w;
}

static std::string escape_json(const std::string& s) {
  std::string out;
  for (char c : s) {
    switch (c) {
      case '"':  out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n";  break;
      case '\r': break;
      case '\t': out += "\\t";  break;
      default:
        if ((unsigned char)c < 0x20) {
          char buf[8];
          sprintf(buf, "\\u%04x", (unsigned char)c);
          out += buf;
        } else {
          out += c;
        }
    }
  }
  return out;
}

static std::string http_post(const std::string& host, int port,
                             const std::string& path,
                             const std::string& json_body) {
  std::string result;
  HINTERNET hSession = WinHttpOpen(L"ErBaiAI-Client/1.0",
      WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, WINHTTP_NO_PROXY_NAME,
      WINHTTP_NO_PROXY_BYPASS, 0);
  if (!hSession) return result;
  HINTERNET hConnect = WinHttpConnect(hSession, to_wide(host).c_str(),
      (INTERNET_PORT)port, 0);
  if (hConnect) {
    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"POST",
        to_wide(path).c_str(), nullptr, WINHTTP_NO_REFERER,
        WINHTTP_DEFAULT_ACCEPT_TYPES, 0);
    if (hRequest) {
      BOOL ok = WinHttpSendRequest(hRequest,
          L"Content-Type: application/json\r\n", (DWORD)-1,
          (LPVOID)json_body.c_str(), (DWORD)json_body.size(),
          (DWORD)json_body.size(), 0);
      if (ok && WinHttpReceiveResponse(hRequest, nullptr)) {
        DWORD avail = 0;
        while (WinHttpQueryDataAvailable(hRequest, &avail) && avail > 0) {
          char buf[8192];
          DWORD read = 0;
          DWORD want = std::min(avail, (DWORD)sizeof(buf));
          if (WinHttpReadData(hRequest, buf, want, &read) && read > 0)
            result.append(buf, read);
        }
      }
      WinHttpCloseHandle(hRequest);
    }
    WinHttpCloseHandle(hConnect);
  }
  WinHttpCloseHandle(hSession);
  return result;
}

int main(int argc, char** argv) {
  std::string text = "检测到疑似勒索软件：尝试连接tor节点并加密磁盘";
  if (argc > 1) text = argv[1];
  std::string body = "{\"text\":\"" + escape_json(text) + "\"}";
  std::string resp = http_post("127.0.0.1", 8765, "/v1/analyze/text", body);
  if (resp.empty()) {
    fprintf(stderr, "请求失败：请确认 AI 服务已启动 (python server.py)\n");
    return 1;
  }
  printf("AI 分析结果: %s\n", resp.c_str());
  return 0;
}
