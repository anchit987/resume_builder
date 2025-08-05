import { useState, useRef, useCallback } from "react";
import { Upload, FileText, Download, Copy, CheckCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";

interface ProcessedResume {
  success: boolean;
  data?: any;
  error?: string;
}

export default function Index() {
  const [file, setFile] = useState<File | null>(null);
  const [userInput, setUserInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedResume, setProcessedResume] = useState<ProcessedResume | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    const validFile = droppedFiles.find(file => 
      file.type === "application/pdf" || 
      file.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    );
    
    if (validFile) {
      setFile(validFile);
    } else {
      toast({
        title: "Invalid file type",
        description: "Please upload a PDF or DOCX file.",
        variant: "destructive",
      });
    }
  }, [toast]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file) {
      toast({
        title: "No file selected",
        description: "Please select a PDF or DOCX file to upload.",
        variant: "destructive",
      });
      return;
    }

    setIsProcessing(true);
    
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("user_input", userInput);

      const response = await fetch("http://localhost:7777/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setProcessedResume({ success: true, data: result });
      
      toast({
        title: "Resume processed successfully!",
        description: "Your resume has been converted to JSON format.",
      });
    } catch (error) {
      console.error("Error processing resume:", error);
      setProcessedResume({ 
        success: false, 
        error: error instanceof Error ? error.message : "Unknown error occurred" 
      });
      
      toast({
        title: "Processing failed",
        description: "Failed to process your resume. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const copyToClipboard = async () => {
    if (processedResume?.data) {
      try {
        await navigator.clipboard.writeText(JSON.stringify(processedResume.data, null, 2));
        toast({
          title: "Copied to clipboard!",
          description: "JSON data has been copied to your clipboard.",
        });
      } catch (error) {
        toast({
          title: "Copy failed",
          description: "Failed to copy to clipboard.",
          variant: "destructive",
        });
      }
    }
  };

  const downloadJson = () => {
    if (processedResume?.data) {
      const dataStr = JSON.stringify(processedResume.data, null, 2);
      const dataBlob = new Blob([dataStr], { type: "application/json" });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${file?.name?.split('.')[0] || 'resume'}_parsed.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }
  };

  const resetForm = () => {
    setFile(null);
    setUserInput("");
    setProcessedResume(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="gradient-purple-blue p-2 rounded-lg">
                <FileText className="h-6 w-6 text-white" />
              </div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-brand-blue-500 bg-clip-text text-transparent">
                Smart Resume Converter
              </h1>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12 space-y-12">
        {/* Hero Section */}
        <section className="text-center space-y-6">
          <h2 className="text-4xl md:text-6xl font-bold tracking-tight">
            Convert Your Resume to{" "}
            <span className="bg-gradient-to-r from-primary to-brand-blue-500 bg-clip-text text-transparent">
              Structured Data
            </span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Upload your PDF or DOCX resume and instantly convert it to structured JSON format.
            Perfect for ATS systems, databases, and modern hiring workflows.
          </p>
        </section>

        {/* Upload Form */}
        <section className="max-w-2xl mx-auto">
          <Card className="gradient-card border-border/50 p-8">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* File Upload Area */}
              <div
                className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-all duration-300 ${
                  isDragOver
                    ? "border-primary bg-primary/5 scale-105"
                    : "border-border hover:border-primary/50 hover:bg-primary/5"
                } ${file ? "border-primary bg-primary/5" : ""}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                
                <div className="space-y-4">
                  {file ? (
                    <div className="flex items-center justify-center space-x-3 text-primary">
                      <CheckCircle className="h-8 w-8" />
                      <div>
                        <p className="font-medium">{file.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {(file.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                  ) : (
                    <>
                      <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
                      <div>
                        <p className="text-lg font-medium">Drop your resume here</p>
                        <p className="text-muted-foreground">
                          or <span className="text-primary underline cursor-pointer">browse files</span>
                        </p>
                        <p className="text-sm text-muted-foreground mt-2">
                          Supports PDF and DOCX formats
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Additional Instructions */}
              <div className="space-y-2">
                <label htmlFor="userInput" className="text-sm font-medium">
                  Additional Instructions (Optional)
                </label>
                <Textarea
                  id="userInput"
                  placeholder="Add any specific instructions for parsing your resume..."
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  className="min-h-[100px] resize-none bg-background/50 border-border/50 focus:border-primary"
                />
              </div>

              {/* Submit Button */}
              <div className="flex space-x-4">
                <Button
                  type="submit"
                  disabled={!file || isProcessing}
                  className="flex-1 gradient-purple-blue hover:scale-105 transition-all duration-300 text-white border-0"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <FileText className="mr-2 h-4 w-4" />
                      Convert Resume
                    </>
                  )}
                </Button>
                
                {(file || processedResume) && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={resetForm}
                    className="hover:scale-105 transition-all duration-300"
                  >
                    Reset
                  </Button>
                )}
              </div>
            </form>
          </Card>
        </section>

        {/* Results Section */}
        {processedResume && (
          <section className="max-w-4xl mx-auto">
            <Card className="gradient-card border-border/50 p-8">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-2xl font-bold">Conversion Results</h3>
                  <div className="flex space-x-3">
                    <Button
                      onClick={copyToClipboard}
                      variant="outline"
                      size="sm"
                      className="hover:scale-105 transition-all duration-300"
                    >
                      <Copy className="mr-2 h-4 w-4" />
                      Copy JSON
                    </Button>
                    <Button
                      onClick={downloadJson}
                      variant="outline"
                      size="sm"
                      className="hover:scale-105 transition-all duration-300"
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Download
                    </Button>
                  </div>
                </div>

                {processedResume.success ? (
                  <div className="bg-background/50 rounded-lg p-6 border border-border/50">
                    <pre className="text-sm overflow-auto max-h-96 text-foreground">
                      {JSON.stringify(processedResume.data, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6">
                    <p className="text-destructive font-medium">
                      Error: {processedResume.error}
                    </p>
                  </div>
                )}
              </div>
            </Card>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border/40 mt-24">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <p className="text-muted-foreground text-sm">
              © 2024 Smart Resume Converter. All rights reserved.
            </p>
            <div className="flex space-x-6 mt-4 md:mt-0">
              <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                Privacy
              </a>
              <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                Terms
              </a>
              <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                Support
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
