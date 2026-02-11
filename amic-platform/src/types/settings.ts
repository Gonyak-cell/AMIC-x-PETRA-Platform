export interface UserPreferences {
  defaultModule: "/" | "/fdd/deals" | "/kiis" | "/im";
  dateFormat: "short" | "long";
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}
