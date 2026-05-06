use std::time::Duration;

use serde::{Deserialize, Serialize};
use serde_json::json;
use serde_json::Value;

#[derive(Debug, Serialize)]
pub struct AnalyzeError {
    pub status: u16,
    pub code: String,
    pub message: String,
    pub fallback: bool,
}

impl AnalyzeError {
    fn new(status: u16, code: &str, message: &str) -> Self {
        Self {
            status,
            code: code.to_string(),
            message: message.to_string(),
            fallback: false,
        }
    }
}

#[derive(Debug, Deserialize)]
pub struct Metadata {
    pub mode: String,
    pub purpose: Option<String>,
}

#[derive(Debug, Serialize)]
struct SessionStartRequest<'a> {
    user_id: &'a str,
    mode: &'a str,
    goal: Option<&'a str>,
}

#[derive(Debug, Deserialize)]
struct SessionStartResponse {
    session_id: String,
    ws_url: String,
}

fn timeout_for(mode: &str) -> Duration {
    match mode {
        "exercise" => Duration::from_secs(60),
        _ => Duration::from_secs(30),
    }
}

#[tauri::command]
pub async fn submit_analysis(
    base_url: String,
    image_bytes: Vec<u8>,
    file_name: String,
    metadata: Metadata,
) -> Result<Value, AnalyzeError> {
    println!(
        "[pc1->pc3] submit_analysis start mode={} file={} bytes={}",
        metadata.mode,
        file_name,
        image_bytes.len()
    );

    let timeout = timeout_for(&metadata.mode);

    let client = reqwest::Client::builder()
        .timeout(timeout)
        .build()
        .map_err(|e| AnalyzeError::new(0, "CLIENT_INIT", &format!("HTTP 클라이언트 초기화 실패: {e}")))?;

    let root = base_url.trim_end_matches('/');
    let start_endpoint = format!("{root}/api/sessions/start");
    println!("[pc1->pc3] session start endpoint={start_endpoint}");

    let goal = if metadata.mode == "exercise" {
        Some("squat")
    } else {
        None
    };

    let start_response = client
        .post(&start_endpoint)
        .json(&SessionStartRequest {
            user_id: "default",
            mode: metadata.mode.as_str(),
            goal,
        })
        .send()
        .await
        .map_err(|e| {
            if e.is_timeout() {
                AnalyzeError::new(504, "TIMEOUT", "세션 시작 요청이 시간 내에 완료되지 않았습니다.")
            } else {
                AnalyzeError::new(0, "NETWORK_ERROR", &format!("서버에 연결할 수 없습니다: {e}"))
            }
        })?;

    let start_status = start_response.status();
    println!("[pc1->pc3] session start status={}", start_status.as_u16());
    if !start_status.is_success() {
        let (code, message) = match start_status.as_u16() {
            400 => ("BAD_REQUEST", "세션 시작 요청 형식이 올바르지 않습니다."),
            500 => ("SERVER_ERROR", "서버 내부 오류로 세션 시작에 실패했습니다."),
            503 => ("SERVICE_UNAVAILABLE", "분석 서버를 일시적으로 사용할 수 없습니다."),
            504 => ("TIMEOUT", "세션 시작 요청이 시간 내에 완료되지 않았습니다."),
            _ => ("HTTP_ERROR", "세션 시작 요청이 실패했습니다."),
        };
        return Err(AnalyzeError::new(start_status.as_u16(), code, message));
    }

    let session: SessionStartResponse = start_response
        .json()
        .await
        .map_err(|e| AnalyzeError::new(0, "INVALID_JSON", &format!("세션 응답 파싱 실패: {e}")))?;
    println!(
        "[pc1->pc3] session created id={} ws_url={}",
        session.session_id,
        session.ws_url
    );

    let mime = if file_name.to_lowercase().ends_with(".png") {
        "image/png"
    } else {
        "image/jpeg"
    };

    let file_part = reqwest::multipart::Part::bytes(image_bytes)
        .file_name(file_name.clone())
        .mime_str(mime)
        .map_err(|e| AnalyzeError::new(0, "MULTIPART", &format!("multipart 구성 실패: {e}")))?;

    let mut form = reqwest::multipart::Form::new()
        .part("file", file_part)
        .text("session_id", session.session_id.clone());

    if let Some(purpose) = metadata.purpose {
        if !purpose.trim().is_empty() {
            form = form.text("purpose", purpose);
        }
    }

    let endpoint = format!("{root}/api/analyze/{}", metadata.mode);
    println!("[pc1->pc3] analyze endpoint={endpoint}");

    let response = client
        .post(&endpoint)
        .multipart(form)
        .send()
        .await
        .map_err(|e| {
            if e.is_timeout() {
                AnalyzeError::new(504, "TIMEOUT", "분석 요청이 시간 내에 완료되지 않았습니다.")
            } else {
                AnalyzeError::new(0, "NETWORK_ERROR", &format!("서버에 연결할 수 없습니다: {e}"))
            }
        })?;

    let status = response.status();
    println!("[pc1->pc3] analyze status={}", status.as_u16());
    if !status.is_success() {
        let (code, message) = match status.as_u16() {
            400 => ("BAD_REQUEST", "요청 형식이 올바르지 않습니다."),
            413 => ("PAYLOAD_TOO_LARGE", "이미지 용량이 너무 큽니다. 더 작은 파일을 사용해주세요."),
            500 => ("SERVER_ERROR", "서버 내부 오류로 분석에 실패했습니다."),
            503 => ("SERVICE_UNAVAILABLE", "분석 서버를 일시적으로 사용할 수 없습니다."),
            504 => ("TIMEOUT", "분석 요청이 시간 내에 완료되지 않았습니다."),
            _ => ("HTTP_ERROR", "분석 요청이 실패했습니다."),
        };
        return Err(AnalyzeError::new(status.as_u16(), code, message));
    }

    let analyze_data: Value = response.json().await.map_err(|e| {
        AnalyzeError::new(status.as_u16(), "INVALID_JSON", &format!("서버 응답을 해석할 수 없습니다: {e}"))
    })?;

    let final_data = if metadata.mode == "exercise" {
        let stop_endpoint = format!("{root}/api/sessions/{}/stop", session.session_id);
        println!("[pc1->pc3] stop endpoint={stop_endpoint}");
        let stop_response = client.post(&stop_endpoint).send().await.map_err(|e| {
            if e.is_timeout() {
                AnalyzeError::new(504, "TIMEOUT", "운동 종료 요청이 시간 내에 완료되지 않았습니다.")
            } else {
                AnalyzeError::new(0, "NETWORK_ERROR", &format!("서버에 연결할 수 없습니다: {e}"))
            }
        })?;

        let stop_status = stop_response.status();
        println!("[pc1->pc3] stop status={}", stop_status.as_u16());
        if !stop_status.is_success() {
            let (code, message) = match stop_status.as_u16() {
                400 => ("BAD_REQUEST", "운동 종료 요청 형식이 올바르지 않습니다."),
                404 => ("SESSION_NOT_FOUND", "세션을 찾을 수 없습니다."),
                500 => ("SERVER_ERROR", "서버 내부 오류로 운동 종료에 실패했습니다."),
                503 => ("SERVICE_UNAVAILABLE", "분석 서버를 일시적으로 사용할 수 없습니다."),
                504 => ("TIMEOUT", "운동 종료 요청이 시간 내에 완료되지 않았습니다."),
                _ => ("HTTP_ERROR", "운동 종료 요청이 실패했습니다."),
            };
            return Err(AnalyzeError::new(stop_status.as_u16(), code, message));
        }

        Some(stop_response.json::<Value>().await.map_err(|e| {
            AnalyzeError::new(
                stop_status.as_u16(),
                "INVALID_JSON",
                &format!("운동 종료 응답을 해석할 수 없습니다: {e}"),
            )
        })?)
    } else {
        None
    };

    Ok(json!({
        "mode": metadata.mode,
        "session": {
            "session_id": session.session_id,
            "ws_url": session.ws_url,
        },
        "analyze": analyze_data,
        "final": final_data,
    }))
}

#[tauri::command]
pub fn ping() -> &'static str {
    "pong"
}
