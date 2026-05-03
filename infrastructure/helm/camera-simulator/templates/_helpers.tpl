{{/*
Common labels
*/}}
{{- define "camera-simulator.labels" -}}
app.kubernetes.io/name: camera-simulator
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: grid-resilience
{{- end }}

{{/*
Selector labels
*/}}
{{- define "camera-simulator.selectorLabels" -}}
app.kubernetes.io/name: camera-simulator
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "camera-simulator.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default "camera-simulator" .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
