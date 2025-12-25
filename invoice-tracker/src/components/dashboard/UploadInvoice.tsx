"use client"

import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { UploadCloud, File as FileIcon, Loader2, X } from "lucide-react"
import { createClient } from "@/supabase/client"
import { toast } from "sonner"
import { useAuth } from "@/components/providers/AuthProvider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useRouter } from "next/navigation"

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

export default function UploadInvoice() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const { user } = useAuth()
  const router = useRouter()
  const supabase = createClient()

  // Helper to convert PDF file to Image Blob
  const convertPdfToImage = async (pdfFile: File): Promise<Blob> => {
    // Dynamically import pdfjs-dist to avoid SSR "DOMMatrix is not defined" error
    const pdfjsLib = await import("pdfjs-dist")
    // Set worker source
    pdfjsLib.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`

    const arrayBuffer = await pdfFile.arrayBuffer()
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
    
    // Get the first page
    const page = await pdf.getPage(1)
    const scale = 2.0 // Higher scale for better quality
    const viewport = page.getViewport({ scale })

    // Create a canvas
    const canvas = document.createElement("canvas")
    const context = canvas.getContext("2d")
    canvas.height = viewport.height
    canvas.width = viewport.width

    if (!context) throw new Error("Could not get canvas context")

    // Render PDF page to canvas
    await page.render({
      canvasContext: context,
      viewport: viewport,
    }).promise

    // Convert canvas to blob (JPEG)
    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (blob) resolve(blob)
        else reject(new Error("Canvas to Blob conversion failed"))
      }, "image/jpeg", 0.95)
    })
  }

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const selectedFile = acceptedFiles[0]
    if (!selectedFile) return

    if (selectedFile.size > MAX_FILE_SIZE) {
      toast.error("File is too large. Max 10MB.")
      return
    }

    try {
        let fileToUpload = selectedFile
        let previewUrl = ""

        // Process PDF or Image
        if (selectedFile.type === "application/pdf") {
            toast.loading("Converting PDF to image...", { id: "conversion" })
            const imageBlob = await convertPdfToImage(selectedFile)
            toast.dismiss("conversion")
            
            // Create a new File object from the Blob
            fileToUpload = new File([imageBlob], selectedFile.name.replace(".pdf", ".jpg"), {
                type: "image/jpeg"
            })
            previewUrl = URL.createObjectURL(imageBlob)
            toast.success("PDF converted successfully")
        } else {
            previewUrl = URL.createObjectURL(selectedFile)
        }

        setFile(fileToUpload)
        setPreview(previewUrl)
    } catch (error) {
        console.error("File processing error:", error)
        toast.error("Failed to process file")
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDragEnter: () => {}, // Handled by hook
    onDragLeave: () => {}, // Handled by hook
    accept: {
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
      "application/pdf": [".pdf"],
    },
    maxFiles: 1,
  })

  const removeFile = (e?: React.MouseEvent) => {
    e?.stopPropagation()
    setFile(null)
    if (preview) URL.revokeObjectURL(preview)
    setPreview(null)
  }

  const handleUpload = async () => {
    if (!file || !user) return

    setIsUploading(true)
    try {
      const fileExt = file.name.split(".").pop()
      const fileName = `${user.id}/${Date.now()}.${fileExt}`
      
      const { error: uploadError } = await supabase.storage
        .from("invoices")
        .upload(fileName, file)

      if (uploadError) throw uploadError

      const { data: { publicUrl } } = supabase.storage
        .from("invoices")
        .getPublicUrl(fileName)

      // Send to API for N8N processing
      const response = await fetch("/api/process-invoice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
           imageUrl: publicUrl,
           userId: user.id
        })
      })

      const result = await response.json()

      if (!response.ok) {
          throw new Error(result.error || "Processing failed")
      }

      toast.success("Invoice uploaded and processed successfully!")
      removeFile()
      router.refresh()
      
    } catch (error: any) {
      console.error("Upload failed", error)
      toast.error(error.message || "Failed to upload invoice")
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Upload Invoice</CardTitle>
        <CardDescription>Drag and drop your invoice here (JPG, PNG, PDF)</CardDescription>
      </CardHeader>
      <CardContent>
        {!file ? (
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors
            ${isDragActive ? "border-primary bg-primary/5 dark:bg-primary/10" : "border-slate-200 dark:border-slate-800 hover:border-primary/50"}
          `}
        >
          <input {...getInputProps()} />
          <UploadCloud className="mx-auto h-12 w-12 text-slate-400 mb-4" />
          <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Drag & drop your invoice here, or click to select
          </p>
          <p className="text-xs text-slate-500 mt-2">
            PNG, JPG, PDF up to 10MB (PDFs converted to Image)
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="relative rounded-lg overflow-hidden border bg-slate-50 dark:bg-slate-900 group">
             <button 
                onClick={removeFile}
                className="absolute top-2 right-2 p-1 bg-white/80 dark:bg-black/50 rounded-full hover:bg-white dark:hover:bg-black transition-colors z-10"
             >
                <X className="h-4 w-4" />
             </button>
             
             {preview ? (
                <div className="relative h-48 w-full">
                     {/* eslint-disable-next-line @next/next/no-img-element */}
                     <img 
                        src={preview} 
                        alt="Preview" 
                        className="w-full h-full object-contain"
                     />
                </div>
             ) : (
                <div className="h-32 flex flex-col items-center justify-center p-4">
                    <FileIcon className="h-12 w-12 text-slate-400 mb-2" />
                    <span className="text-sm truncate max-w-full px-4">{file.name}</span>
                </div>
             )}
          </div>

          <div className="flex gap-2 justify-end">
            <Button
                variant="outline"
                onClick={removeFile}
                disabled={isUploading}
            >
                Cancel
            </Button>
            <Button
                onClick={handleUpload}
                disabled={isUploading}
            >
                {isUploading ? (
                    <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Processing...
                    </>
                ) : (
                    "Upload & Process"
                )}
            </Button>
          </div>
        </div>
      )}
      </CardContent>
    </Card>
  )
}
