import React, { useEffect, useRef } from 'react';

function PDFViewer({ fileUrl, onSectionChange }) {
  const viewerRef = useRef(null);

  useEffect(() => {
    if (fileUrl && viewerRef.current) {
      const adobeDCView = new window.AdobeDC.View({
        clientId: "<YOUR_ADOBE_CLIENT_ID>", // Replace with your Adobe Client ID
        divId: viewerRef.current.id,
      });

      adobeDCView.previewFile(
        {
          content: { location: { url: fileUrl } },
          metaData: { fileName: "document.pdf" },
        },
        {
          embedMode: "IN_LINE",
          showAnnotations: true,
          showLeftHandPanel: true,
        }
      );

      // ✅ Listen for PAGE_VIEW event
      adobeDCView.registerCallback(
        window.AdobeDC.View.Enum.CallbackType.EVENT_LISTENER,
        (event) => {
          if (event.type === "PAGE_VIEW") {
            // event.data.pageNumber starts from 1
            onSectionChange(event.data.pageNumber - 1);
          }
        },
        { listenOn: [window.AdobeDC.View.Enum.Events.PAGE_VIEW] }
      );
    }
  }, [fileUrl, onSectionChange]);

  return <div id="adobe-dc-view" ref={viewerRef} style={{ height: "100%" }} />;
}

export default PDFViewer;
