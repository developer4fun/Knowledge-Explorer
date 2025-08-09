import React from 'react';

function FileUpload({ onFileSelect, isLoading }) {
  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      onFileSelect(file);
    }
  };

  return (
    <div className="mb-4">
      <label htmlFor="pdf-upload" className="block text-sm font-medium text-gray-700 mb-2">
        Upload PDF
      </label>
      <input
        id="pdf-upload"
        type="file"
        accept=".pdf"
        onChange={handleFileChange}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-violet-50 file:text-violet-700 hover:file:bg-violet-100"
        disabled={isLoading}
      />
      {isLoading && <p className="text-sm text-gray-500 mt-2">Processing...</p>}
    </div>
  );
}

export default FileUpload;