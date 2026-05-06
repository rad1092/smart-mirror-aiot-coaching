type CameraPreviewProps = {
  previewUrl: string | null;
  alt?: string;
  emptyMessage?: string;
};

function CameraPreview({
  previewUrl,
  alt = "촬영한 이미지 미리보기",
  emptyMessage = "아직 선택된 이미지가 없습니다.",
}: CameraPreviewProps) {
  return (
    <div className="camera-preview" aria-live="polite">
      {previewUrl ? (
        <img src={previewUrl} alt={alt} className="camera-preview__image" />
      ) : (
        <div className="camera-preview__empty" role="status">
          {emptyMessage}
        </div>
      )}
    </div>
  );
}

export default CameraPreview;
