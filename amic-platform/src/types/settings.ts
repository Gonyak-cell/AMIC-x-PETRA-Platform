export interface UserPreferences {
  defaultModule: "/" | "/ma/transactions" | "/docs" | "/kiis";
  dateFormat: "short" | "long";
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}
