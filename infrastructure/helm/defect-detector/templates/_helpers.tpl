{{/*
Common labels
*/}}
{{- define "defect-detector.labels" -}}
app.kubernetes.io/name: defect-detector
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: grid-resilience
{{- end }}

{{/*
Selector labels
*/}}
{{- define "defect-detector.selectorLabels" -}}
app.kubernetes.io/name: defect-detector
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "defect-detector.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default "defect-detector" .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
